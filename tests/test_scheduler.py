from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from windiq import scheduler
from windiq.database import Base
from windiq.models import SyncState


def test_scheduler_skips_a_collection_interval_that_already_succeeded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(scheduler, "get_session_factory", lambda: sessions)
    now = datetime(2026, 10, 27, 19, 4, tzinfo=UTC)
    try:
        with sessions() as session:
            session.add(
                SyncState(
                    stream="measurements",
                    last_success_at=now - timedelta(minutes=4),
                )
            )
            session.commit()

        assert scheduler._already_succeeded_this_interval(now.timestamp(), 3600)
        assert not scheduler._already_succeeded_this_interval(
            (now + timedelta(hours=1)).timestamp(), 3600
        )
    finally:
        engine.dispose()


def test_scheduler_does_not_collect_again_after_restart(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        scheduler, "get_settings", lambda: SimpleNamespace(ingest_interval_seconds=3600)
    )
    monkeypatch.setattr(scheduler, "_already_succeeded_this_interval", lambda *_: True)
    monkeypatch.setattr(
        scheduler, "ingest_once", lambda: pytest.fail("extra ingestion")
    )
    monkeypatch.setattr(scheduler.time, "time", lambda: 7201.0)

    def stop_after_wait(_seconds: float) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(scheduler.time, "sleep", stop_after_wait)
    assert scheduler.main() == 0
