from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from windiq.config import get_settings
from windiq.ingest import _should_update, ingest_measurements, parse_measurement
from windiq.models import IngestionRun, Measurement, SyncState

ROOT = Path(__file__).resolve().parents[1]


class FakeClient:
    def __init__(self, pages: list[dict[str, object]]) -> None:
        self.pages = pages
        self.updated_since: datetime | None = None

    def iter_measurement_pages(
        self, *, updated_since: datetime | None = None
    ) -> Iterator[dict[str, object]]:
        self.updated_since = updated_since
        yield from self.pages

    def get_mast_id(self) -> str:
        return "mast-1"


@pytest.fixture
def sessions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[sessionmaker[Session]]:
    url = f"sqlite+pysqlite:///{tmp_path / 'ingest.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    command.upgrade(config, "head")
    engine = create_engine(url)
    try:
        yield sessionmaker(bind=engine, expire_on_commit=False)
    finally:
        engine.dispose()
        get_settings.cache_clear()


def sample_record(**changes: object) -> dict[str, object]:
    return {
        "timestamp": "2026-10-01T00:00:00+00:00",
        "wind_speed": None,
        "unit": "m/s",
        "wind_direction_deg": None,
        "updated_at": "2026-10-02T00:00:00+00:00",
        "version": "v1",
    } | changes


def test_insert_and_checkpoint_after_all_pages(sessions: sessionmaker[Session]) -> None:
    client = FakeClient(
        [
            {"data": [sample_record()], "next_cursor": "page-2"},
            {"data": [], "next_cursor": None},
        ]
    )
    summary = ingest_measurements(client, sessions)

    assert (
        summary.records_seen,
        summary.records_inserted,
        summary.records_updated,
    ) == (
        1,
        1,
        0,
    )
    assert client.updated_since is None
    with sessions() as session:
        measurement = session.scalar(select(Measurement))
        assert measurement is not None
        assert measurement.wind_speed is None
        assert measurement.wind_direction_deg is None
        assert measurement.upstream_version == "v1"
        state = session.get(SyncState, "measurements")
        assert state is not None
        assert state.last_successful_updated_since is not None
        assert state.last_successful_updated_since.isoformat().startswith("2026-10-02")
        run = session.get(IngestionRun, summary.run_id)
        assert run is not None
        assert run.status == "succeeded"


def test_later_page_failure_rolls_back_data_and_checkpoint(
    sessions: sessionmaker[Session],
) -> None:
    ingest_measurements(
        FakeClient([{"data": [sample_record()], "next_cursor": None}]), sessions
    )
    client = FakeClient(
        [
            {
                "data": [
                    sample_record(
                        timestamp="2026-10-01T01:00:00+00:00",
                        updated_at="2026-10-03T00:00:00+00:00",
                    ),
                    {"unit": ""},
                ],
                "next_cursor": None,
            }
        ]
    )
    with pytest.raises(ValueError, match="unit"):
        ingest_measurements(client, sessions)

    assert client.updated_since is not None
    assert client.updated_since.isoformat().startswith("2026-10-01T23:59:59")
    with sessions() as session:
        assert len(session.scalars(select(Measurement)).all()) == 1
        state = session.get(SyncState, "measurements")
        assert state is not None
        assert state.last_successful_updated_since is not None
        assert state.last_successful_updated_since.isoformat().startswith("2026-10-02")
        runs = session.scalars(select(IngestionRun).order_by(IngestionRun.id)).all()
        assert [run.status for run in runs] == ["succeeded", "failed"]
        assert runs[-1].error_summary == "ValueError"
        assert runs[-1].records_inserted == 0


def test_repeated_page_is_idempotent(sessions: sessionmaker[Session]) -> None:
    page = {"data": [sample_record()], "next_cursor": None}
    ingest_measurements(FakeClient([page]), sessions)
    second = ingest_measurements(FakeClient([page]), sessions)
    assert (second.records_seen, second.records_inserted, second.records_updated) == (
        1,
        0,
        0,
    )
    with sessions() as session:
        assert len(session.scalars(select(Measurement)).all()) == 1


def test_newer_correction_updates_existing_row(sessions: sessionmaker[Session]) -> None:
    ingest_measurements(
        FakeClient([{"data": [sample_record()], "next_cursor": None}]), sessions
    )
    corrected = sample_record(
        wind_speed=8.5,
        updated_at="2026-10-03T00:00:00+00:00",
        version="v2",
    )
    summary = ingest_measurements(
        FakeClient([{"data": [corrected], "next_cursor": None}]), sessions
    )
    assert (summary.records_inserted, summary.records_updated) == (0, 1)
    with sessions() as session:
        measurements = session.scalars(select(Measurement)).all()
        assert len(measurements) == 1
        assert measurements[0].wind_speed == 8.5
        assert measurements[0].upstream_version == "v2"
        state = session.get(SyncState, "measurements")
        assert state is not None
        assert state.last_successful_updated_since is not None
        assert state.last_successful_updated_since.isoformat().startswith("2026-10-03")


def test_parse_preserves_missing_values_and_rejects_invalid_source_values() -> None:
    record = parse_measurement(sample_record(), mast_id="mast-1")
    assert record.wind_speed is None
    assert record.wind_direction_deg is None
    invalid = parse_measurement(
        sample_record(wind_speed="invalid", version=2), mast_id="mast-1"
    )
    assert invalid.wind_speed is None
    assert invalid.source_payload["wind_speed"] == "invalid"
    assert invalid.upstream_version == "2"


def test_invalid_source_reading_is_stored_without_zero(
    sessions: sessionmaker[Session],
) -> None:
    ingest_measurements(
        FakeClient(
            [
                {
                    "data": [sample_record(wind_speed="invalid")],
                    "next_cursor": None,
                }
            ]
        ),
        sessions,
    )
    with sessions() as session:
        measurement = session.scalar(select(Measurement))
        assert measurement is not None
        assert measurement.wind_speed is None
        assert measurement.source_payload is not None
        assert measurement.source_payload["wind_speed"] == "invalid"


def test_correction_and_stale_record_decisions() -> None:
    source = parse_measurement(sample_record(), mast_id="mast-1")
    existing = Measurement(
        mast_id=source.mast_id,
        timestamp=source.timestamp,
        wind_speed=source.wind_speed,
        unit=source.unit,
        wind_direction_deg=source.wind_direction_deg,
        upstream_updated_at=source.upstream_updated_at,
        upstream_version=source.upstream_version,
        ingested_at=datetime.now(UTC),
        source_payload=source.source_payload,
    )
    assert not _should_update(existing, source)
    assert _should_update(
        existing,
        parse_measurement(
            sample_record(updated_at="2026-10-03T00:00:00+00:00", wind_speed=8),
            mast_id="mast-1",
        ),
    )
    assert not _should_update(
        existing,
        parse_measurement(
            sample_record(updated_at="2026-10-01T00:00:00+00:00", wind_speed=8),
            mast_id="mast-1",
        ),
    )
