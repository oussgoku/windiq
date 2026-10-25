from datetime import UTC, datetime

import httpx
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

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
