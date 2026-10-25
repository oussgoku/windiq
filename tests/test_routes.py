from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from windiq import routes
from windiq.database import Base
from windiq.models import IngestionRun, SyncState


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
