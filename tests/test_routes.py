from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from windiq import routes
from windiq.database import Base
from windiq.models import IngestionRun, Measurement, SyncState


def test_ingestion_health_reports_failed_and_stale_runs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(routes, "get_session_factory", lambda: sessions)
    monkeypatch.setattr(
        routes, "get_settings", lambda: SimpleNamespace(ingest_stale_after_seconds=9000)
    )
    now = datetime.now(UTC)
    try:
        with sessions() as session:
            session.add(SyncState(stream="measurements", last_success_at=now))
            session.add(
                IngestionRun(started_at=now, finished_at=now, status="succeeded")
            )
            session.commit()

        assert routes.ingestion_health()["status"] == "ok"

        with sessions() as session:
            latest = session.get(IngestionRun, 1)
            assert latest is not None
            latest.status = "failed"
            session.commit()
        with pytest.raises(HTTPException, match="latest ingestion failed"):
            routes.ingestion_health()

        with sessions() as session:
            latest = session.get(IngestionRun, 1)
            state = session.get(SyncState, "measurements")
            assert latest is not None and state is not None
            latest.status = "succeeded"
            state.last_success_at = now - timedelta(hours=3)
            session.commit()
        with pytest.raises(HTTPException, match="ingestion is stale"):
            routes.ingestion_health()
    finally:
        engine.dispose()


def test_dashboard_context_uses_stored_measurements_and_runs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    now = datetime.now(UTC)

    class FakeClient:
        def __init__(self, _settings: object) -> None:
            pass

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, *_args: object) -> None:
            pass

        def get_mast(self) -> dict[str, object]:
            return {"id": "mast-1", "measurement_height_m": 100}

        def get_site(self) -> dict[str, object]:
            return {
                "mast_id": "mast-1",
                "name": "Test site",
                "shear_exponent": 0.2,
                "losses": {"availability": 0.05, "electrical": 0.02, "wake": 0.06},
                "uncertainty": 0.08,
            }

        def get_turbine(self) -> dict[str, object]:
            return {
                "hub_height_m": 140,
                "rated_power_kw": 3600,
                "cut_in_wind_speed_ms": 3,
                "cut_out_wind_speed_ms": 25,
                "power_curve": [
                    {"wind_speed_ms": 3, "power_kw": 0},
                    {"wind_speed_ms": 10, "power_kw": 3600},
                    {"wind_speed_ms": 25, "power_kw": 0},
                ],
            }

    monkeypatch.setattr(routes, "WindIQClient", FakeClient)
    monkeypatch.setattr(routes, "get_session_factory", lambda: sessions)
    monkeypatch.setattr(
        routes,
        "get_settings",
        lambda: SimpleNamespace(
            ingest_stale_after_seconds=9000,
            ingest_interval_seconds=3600,
            dashboard_data_mode="live",
        ),
    )
    try:
        with sessions() as session:
            session.add(SyncState(stream="measurements", last_success_at=now))
            session.add(
                IngestionRun(started_at=now, finished_at=now, status="succeeded")
            )
            session.add(
                Measurement(
                    mast_id="mast-1",
                    timestamp=now,
                    wind_speed=7.8,
                    unit="m/s",
                    upstream_updated_at=now,
                    upstream_version="1",
                    ingested_at=now,
                )
            )
            session.commit()

        result = routes.dashboard_context()
        assert result["site_name"] == "Test site"
        assert result["data_mode"] == "live"
        assert result["rated_power_mw"] == 3.6
        assert result["collection_healthy"] is True
        assert result["next_sync_at"].minute == 0
        recent = result["recent_measurements"]
        assert isinstance(recent, list)
        assert recent[0]["wind_mast_ms"] == 7.8
        assert recent[0]["wind_hub_ms"] > 7.8
        assert recent[0]["power_mw"] > 0
    finally:
        engine.dispose()
