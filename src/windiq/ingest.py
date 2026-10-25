"""Run measurement ingestion once with ``python -m windiq.ingest``."""

import logging
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import isnan

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from windiq.config import get_settings
from windiq.database import get_session_factory
from windiq.models import IngestionRun, Measurement, SyncState
from windiq.upstream import WindIQClient

logger = logging.getLogger(__name__)
STREAM = "measurements"


def _safe_error_summary(exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        return f"HTTP {exc.response.status_code} {exc.request.url.path}"
    return type(exc).__name__


@dataclass(frozen=True)
class SourceMeasurement:
    mast_id: str
    timestamp: datetime
    wind_speed: float | None
    unit: str
    wind_direction_deg: float | None
    upstream_updated_at: datetime
    upstream_version: str
    source_payload: dict[str, object]


@dataclass(frozen=True)
class IngestionSummary:
    run_id: int
    records_seen: int
    records_inserted: int
    records_updated: int


def _identifier(value: object, name: str) -> str:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError(f"{name} must be a string or integer")
    result = str(value)
    if not result:
        raise ValueError(f"{name} must not be empty")
    return result


def _timestamp(value: object, name: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be an ISO 8601 string")
    try:
        result = datetime.fromisoformat(value)
    except ValueError:
        raise ValueError(f"{name} must be an ISO 8601 string") from None
    if result.utcoffset() is None:
        raise ValueError(f"{name} must include a timezone")
    return result


def _database_timestamp(value: datetime) -> datetime:
    # PostgreSQL returns aware values; SQLite used in tests drops the UTC marker.
    return value if value.utcoffset() is not None else value.replace(tzinfo=UTC)


def _numeric_or_none(value: object) -> float | None:
    # Invalid or missing readings stay in source_payload and are excluded later.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def parse_measurement(
    record: object, *, mast_id: str | None = None
) -> SourceMeasurement:
    """Map a source measurement, using the single mast resource when needed."""
    if not isinstance(record, dict):
        raise ValueError("measurement must be a JSON object")
    record_mast_id = record.get("mast_id")
    if record_mast_id is None:
        if mast_id is None:
            raise ValueError("measurement has no mast_id and no mast resource id")
        record_mast_id = mast_id
    elif mast_id is not None and _identifier(record_mast_id, "mast_id") != mast_id:
        raise ValueError("measurement mast_id disagrees with mast resource")
    unit = record.get("unit")
    if not isinstance(unit, str) or not unit:
        raise ValueError("unit must be a nonempty string")
    updated_at = record.get("updated_at", record.get("upstream_updated_at"))
    version = record.get("version", record.get("upstream_version"))
    return SourceMeasurement(
        mast_id=_identifier(record_mast_id, "mast_id"),
        timestamp=_timestamp(record.get("timestamp"), "timestamp"),
        wind_speed=_numeric_or_none(record.get("wind_speed")),
        unit=unit,
        wind_direction_deg=_numeric_or_none(record.get("wind_direction_deg")),
        upstream_updated_at=_timestamp(updated_at, "updated_at"),
        upstream_version=_identifier(version, "version"),
        source_payload=dict(record),
    )


def _records(page: dict[str, object]) -> list[object]:
    records = page.get("data")
    if not isinstance(records, list):
        raise ValueError("measurements response must contain a data array")
    return records


def _upsert(session: Session, source: SourceMeasurement, now: datetime) -> str:
    existing = session.scalar(
        select(Measurement).where(
            Measurement.mast_id == source.mast_id,
            Measurement.timestamp == source.timestamp,
        )
    )
    if existing is None:
        session.add(
            Measurement(
                mast_id=source.mast_id,
                timestamp=source.timestamp,
                wind_speed=source.wind_speed,
                unit=source.unit,
                wind_direction_deg=source.wind_direction_deg,
                upstream_updated_at=source.upstream_updated_at,
                upstream_version=source.upstream_version,
                ingested_at=now,
                source_payload=source.source_payload,
            )
        )
        return "inserted"

    if not _should_update(existing, source):
        return "unchanged"
    fields = (
        "wind_speed",
        "unit",
        "wind_direction_deg",
        "upstream_updated_at",
        "upstream_version",
        "source_payload",
    )
    for field in fields:
        setattr(existing, field, getattr(source, field))
    existing.ingested_at = now
    return "updated"


def _same_value(left: object, right: object) -> bool:
    if isinstance(left, float) and isinstance(right, float):
        if isnan(left) and isnan(right):
            return True
    return left == right


def _should_update(existing: Measurement, source: SourceMeasurement) -> bool:
    if source.upstream_updated_at < _database_timestamp(existing.upstream_updated_at):
        return False
    fields = (
        "wind_speed",
        "unit",
        "wind_direction_deg",
        "upstream_updated_at",
        "upstream_version",
        "source_payload",
    )
    return any(
        not _same_value(
            _database_timestamp(getattr(existing, field))
            if field == "upstream_updated_at"
            else getattr(existing, field),
            getattr(source, field),
        )
        for field in fields
    )


def ingest_measurements(
    client: WindIQClient,
    session_factory: Callable[[], Session] | None = None,
) -> IngestionSummary:
    """Commit all pages and the checkpoint together, or keep the prior state."""
    if session_factory is None:
        session_factory = get_session_factory()
    started_at = datetime.now(UTC)
    with session_factory() as session:
        run = IngestionRun(started_at=started_at, status="running")
        session.add(run)
        session.commit()
        run_id = run.id

    seen = inserted = updated = 0
    try:
        with session_factory() as session:
            with session.begin():
                state = session.get(SyncState, STREAM)
                if state is None:
                    state = SyncState(stream=STREAM)
                    session.add(state)
                checkpoint = state.last_successful_updated_since
                if checkpoint is not None:
                    checkpoint = _database_timestamp(checkpoint)
                # Re-read a small boundary window in case updated_since is exclusive.
                query_since = checkpoint - timedelta(seconds=1) if checkpoint else None
                mast_id = client.get_mast_id()
                for page in client.iter_measurement_pages(updated_since=query_since):
                    for raw_record in _records(page):
                        seen += 1
                        source = parse_measurement(raw_record, mast_id=mast_id)
                        outcome = _upsert(session, source, datetime.now(UTC))
                        inserted += outcome == "inserted"
                        updated += outcome == "updated"
                        if (
                            checkpoint is None
                            or source.upstream_updated_at > checkpoint
                        ):
                            checkpoint = source.upstream_updated_at

                now = datetime.now(UTC)
                state.last_successful_updated_since = checkpoint
                state.last_success_at = now
                run = session.get(IngestionRun, run_id)
                if run is None:
                    raise RuntimeError("ingestion run disappeared")
                run.finished_at = now
                run.status = "succeeded"
                run.records_seen = seen
                run.records_inserted = inserted
                run.records_updated = updated
    except Exception as exc:
        summary = _safe_error_summary(exc)
        logger.error("Ingestion run %s failed: %s", run_id, summary)
        with session_factory() as session:
            run = session.get(IngestionRun, run_id)
            if run is not None:
                run.finished_at = datetime.now(UTC)
                run.status = "failed"
                run.records_seen = seen
                run.error_summary = summary
                session.commit()
        raise

    return IngestionSummary(run_id, seen, inserted, updated)


def main() -> int:
    try:
        with WindIQClient(get_settings()) as client:
            summary = ingest_measurements(client)
    except Exception as exc:
        print(f"Ingestion failed ({_safe_error_summary(exc)})", file=sys.stderr)
        return 1
    print(
        f"Run {summary.run_id}: {summary.records_seen} seen, "
        f"{summary.records_inserted} inserted, {summary.records_updated} updated"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
