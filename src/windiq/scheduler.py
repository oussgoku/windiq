"""Run missing intervals, then collect on each UTC interval boundary."""

import time
from datetime import UTC, datetime

from sqlalchemy.exc import SQLAlchemyError

from windiq.config import get_settings
from windiq.database import get_session_factory
from windiq.ingest import main as ingest_once
from windiq.models import SyncState


def _already_succeeded_this_interval(now: float, interval: int) -> bool:
    boundary = datetime.fromtimestamp(int(now // interval) * interval, UTC)
    try:
        with get_session_factory()() as session:
            state = session.get(SyncState, "measurements")
    except SQLAlchemyError:
        return False
    if state is None or state.last_success_at is None:
        return False
    last_success = state.last_success_at
    if last_success.utcoffset() is None:
        last_success = last_success.replace(tzinfo=UTC)
    return last_success >= boundary


def main() -> int:
    interval = get_settings().ingest_interval_seconds
    try:
        while True:
            if not _already_succeeded_this_interval(time.time(), interval):
                ingest_once()
            now = time.time()
            next_run = (int(now // interval) + 1) * interval
            time.sleep(max(1, next_run - now))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
