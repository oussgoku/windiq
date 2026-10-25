"""Run ingestion immediately, then on each UTC interval boundary."""

import time

from windiq.config import get_settings
from windiq.ingest import main as ingest_once


def main() -> int:
    interval = get_settings().ingest_interval_seconds
    try:
        while True:
            ingest_once()
            now = time.time()
            next_run = (int(now // interval) + 1) * interval
            time.sleep(max(1, next_run - now))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
