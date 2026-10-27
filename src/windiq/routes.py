from datetime import UTC, datetime
from math import isfinite

import httpx
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

from windiq.calculations import hub_wind_speed, power_at_wind_speed
from windiq.config import get_settings
from windiq.database import get_session_factory
from windiq.energy import (
    AnnualEnergyResult,
    EnergyResult,
    HourlyReading,
    annual_window,
    annualize,
    calculate_window,
    parse_energy_parameters,
    validate_window,
)
from windiq.models import IngestionRun, Measurement, SyncState
from windiq.upstream import WindIQClient

router = APIRouter()


@router.get("/ingestion/runs")
def ingestion_runs(
    limit: int = Query(default=20, ge=1, le=100),
    before_id: int | None = Query(default=None, ge=1),
) -> dict[str, object]:
    """Return collection runs in newest-first pages without discarding history."""
    query = select(IngestionRun).order_by(IngestionRun.id.desc()).limit(limit + 1)
    if before_id is not None:
        query = query.where(IngestionRun.id < before_id)
    try:
        with get_session_factory()() as session:
            page = session.scalars(query).all()
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc

    has_more = len(page) > limit
    runs = page[:limit]
    return {
        "runs": [
            {
                "id": run.id,
                "started_at": run.started_at,
                "finished_at": run.finished_at,
                "status": run.status,
                "records_seen": run.records_seen,
                "records_inserted": run.records_inserted,
                "records_updated": run.records_updated,
                "error_summary": run.error_summary,
            }
            for run in runs
        ],
        "next_before_id": runs[-1].id if has_more else None,
    }


@router.get("/dashboard/context")
def dashboard_context() -> dict[str, object]:
    """Current inputs, recent readings, and ingestion history for the dashboard."""
    try:
        with WindIQClient(get_settings()) as client:
            mast = client.get_mast()
            site = client.get_site()
            turbine = client.get_turbine()
        mast_id, site_parameters, turbine_parameters = parse_energy_parameters(
            mast, site, turbine
        )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="upstream API unavailable") from exc
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=502, detail="invalid upstream parameters"
        ) from exc

    try:
        with get_session_factory()() as session:
            measurements = session.scalars(
                select(Measurement)
                .where(Measurement.mast_id == mast_id)
                .order_by(Measurement.timestamp.desc())
                .limit(3)
            ).all()
            runs = session.scalars(
                select(IngestionRun).order_by(IngestionRun.id.desc()).limit(4)
            ).all()
            state = session.get(SyncState, "measurements")
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc

    recent = []
    for measurement in measurements:
        speed = measurement.wind_speed
        if speed is not None and isfinite(speed) and speed >= 0:
            if measurement.unit == "km/h":
                speed /= 3.6
            elif measurement.unit != "m/s":
                speed = None
        else:
            speed = None
        hub_speed = (
            hub_wind_speed(speed, site_parameters) if speed is not None else None
        )
        power_mw = (
            power_at_wind_speed(hub_speed, turbine_parameters) / 1000
            if hub_speed is not None
            else None
        )
        recent.append(
            {
                "timestamp": measurement.timestamp,
                "wind_mast_ms": speed,
                "wind_hub_ms": hub_speed,
                "power_mw": power_mw,
            }
        )

    last_success = state.last_success_at if state else None
    if last_success is not None and last_success.utcoffset() is None:
        last_success = last_success.replace(tzinfo=UTC)
    latest_status = runs[0].status if runs else None
    age_seconds = (
        max(0, int((datetime.now(UTC) - last_success).total_seconds()))
        if last_success is not None
        else None
    )
    healthy = (
        latest_status == "succeeded"
        and age_seconds is not None
        and age_seconds <= get_settings().ingest_stale_after_seconds
    )
    interval = get_settings().ingest_interval_seconds
    next_boundary = (int(datetime.now(UTC).timestamp() // interval) + 1) * interval
    data_mode = getattr(get_settings(), "dashboard_data_mode", "live")
    next_sync = (
        datetime.fromtimestamp(next_boundary, UTC) if data_mode == "live" else None
    )

    return {
        "data_mode": data_mode,
        "mast_id": mast_id,
        "site_name": site.get("name") or mast.get("name") or mast_id,
        "rated_power_mw": turbine_parameters.rated_power_kw / 1000,
        "inputs": {
            "measurement_height_m": site_parameters.measurement_height_m,
            "hub_height_m": site_parameters.hub_height_m,
            "shear_exponent": site_parameters.shear_exponent,
            "availability_loss": site_parameters.availability_loss,
            "electrical_loss": site_parameters.electrical_loss,
            "wake_loss": site_parameters.wake_loss,
            "uncertainty": site_parameters.uncertainty,
        },
        "latest_measurement_at": measurements[0].timestamp if measurements else None,
        "last_success_at": last_success,
        "next_sync_at": next_sync,
        "collection_healthy": healthy,
        "recent_measurements": recent,
        "recent_runs": [
            {
                "started_at": run.started_at,
                "finished_at": run.finished_at,
                "status": run.status,
                "records_seen": run.records_seen,
                "error_summary": run.error_summary,
            }
            for run in runs
        ],
    }


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def ready() -> dict[str, str]:
    try:
        with get_session_factory()() as session:
            session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return {"status": "ok"}


@router.get("/health/ingestion")
def ingestion_health() -> dict[str, str | int | None]:
    """A probe for a failed or stale hourly ingestion cycle."""
    try:
        with get_session_factory()() as session:
            state = session.get(SyncState, "measurements")
            latest = session.scalar(
                select(IngestionRun).order_by(IngestionRun.id.desc()).limit(1)
            )
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc

    if state is None or state.last_success_at is None or latest is None:
        raise HTTPException(status_code=503, detail="ingestion has not succeeded")
    last_success = state.last_success_at
    if last_success.utcoffset() is None:
        last_success = last_success.replace(tzinfo=UTC)
    age_seconds = max(0, int((datetime.now(UTC) - last_success).total_seconds()))
    if latest.status == "failed":
        raise HTTPException(status_code=503, detail="latest ingestion failed")
    if age_seconds > get_settings().ingest_stale_after_seconds:
        raise HTTPException(status_code=503, detail="ingestion is stale")
    return {
        "status": "ok",
        "last_success_at": last_success.isoformat(),
        "seconds_since_success": age_seconds,
        "latest_run_status": latest.status,
    }


@router.get("/energy", response_model=EnergyResult)
def energy(
    start: datetime = Query(description="Inclusive UTC-aligned hour with timezone"),
    end: datetime = Query(description="Exclusive UTC-aligned hour with timezone"),
) -> EnergyResult:
    return _calculate_energy(start, end)


@router.get("/energy/annual", response_model=AnnualEnergyResult)
def annual_energy() -> AnnualEnergyResult:
    start, end = annual_window()
    return annualize(_calculate_energy(start, end))


def _calculate_energy(start: datetime, end: datetime) -> EnergyResult:
    try:
        start_utc, end_utc, _ = validate_window(start, end)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        with WindIQClient(get_settings()) as client:
            mast = client.get_mast()
            site = client.get_site()
            turbine = client.get_turbine()
        mast_id, site_parameters, turbine_parameters = parse_energy_parameters(
            mast, site, turbine
        )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="upstream API unavailable") from exc
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=502, detail="invalid upstream parameters"
        ) from exc

    try:
        with get_session_factory()() as session:
            rows = session.execute(
                select(
                    Measurement.timestamp,
                    Measurement.wind_speed,
                    Measurement.unit,
                    Measurement.source_payload,
                )
                .where(
                    Measurement.mast_id == mast_id,
                    Measurement.timestamp >= start_utc,
                    Measurement.timestamp < end_utc,
                )
                .order_by(Measurement.timestamp)
            ).all()
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc

    readings = [HourlyReading(*row) for row in rows]
    return calculate_window(
        readings,
        mast_id=mast_id,
        start=start_utc,
        end=end_utc,
        site=site_parameters,
        turbine=turbine_parameters,
    )
