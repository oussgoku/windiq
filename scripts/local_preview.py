"""Run the real API and frontend with isolated, generated PostgreSQL data."""

from datetime import UTC, datetime, timedelta
from math import pi, sin
from os import environ

import uvicorn
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from windiq import routes
from windiq.database import Base
from windiq.energy import annual_window
from windiq.main import app
from windiq.models import IngestionRun, Measurement, SyncState

url = make_url(environ["DATABASE_URL"])
if (
    environ.get("WINDIQ_PREVIEW") != "1"
    or url.host != "db"
    or url.database != "windiq_preview"
):
    raise RuntimeError("local preview requires its isolated test database")

engine = create_engine(url)
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
sessions = sessionmaker(bind=engine, expire_on_commit=False)
now = datetime.now(UTC)
start, end = annual_window(now)
rows = []
cursor = start
index = 0
while cursor < end:
    if index % 75 != 0:
        speed = (
            7 + 2.2 * sin(2 * pi * index / (24 * 365)) + 1.1 * sin(2 * pi * index / 24)
        )
        is_kmh = index % 13 == 0
        rows.append(
            Measurement(
                mast_id="WIQ-MM-01",
                timestamp=cursor,
                wind_speed=speed * 3.6 if is_kmh else speed,
                unit="km/h" if is_kmh else "m/s",
                upstream_updated_at=now,
                upstream_version="local-fixture",
                ingested_at=now,
            )
        )
    cursor += timedelta(hours=1)
    index += 1

cursor = end
current_hour = now.replace(minute=0, second=0, microsecond=0)
while cursor <= current_hour:
    rows.append(
        Measurement(
            mast_id="WIQ-MM-01",
            timestamp=cursor,
            wind_speed=7 + cursor.hour % 3,
            unit="m/s",
            upstream_updated_at=now,
            upstream_version="local-fixture",
            ingested_at=now,
        )
    )
    cursor += timedelta(hours=1)

with sessions() as session:
    session.bulk_save_objects(rows)
    session.add(SyncState(stream="measurements", last_success_at=now))
    session.add(
        IngestionRun(
            started_at=now - timedelta(minutes=1),
            finished_at=now,
            status="succeeded",
            records_seen=len(rows),
            records_inserted=len(rows),
            records_updated=0,
        )
    )
    session.commit()


class FixtureClient:
    """Supply test calculation inputs without contacting the upstream service."""

    def __init__(self, _settings: object) -> None:
        pass

    def __enter__(self) -> "FixtureClient":
        return self

    def __exit__(self, *_args: object) -> None:
        pass

    def get_mast(self) -> dict[str, object]:
        return {"id": "WIQ-MM-01", "measurement_height_m": 100}

    def get_site(self) -> dict[str, object]:
        return {
            "mast_id": "WIQ-MM-01",
            "name": "Local test fixture",
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
                {"wind_speed_ms": 5, "power_kw": 500},
                {"wind_speed_ms": 7, "power_kw": 1500},
                {"wind_speed_ms": 9, "power_kw": 2700},
                {"wind_speed_ms": 12, "power_kw": 3600},
                {"wind_speed_ms": 25, "power_kw": 0},
            ],
        }


routes.WindIQClient = FixtureClient
routes.get_session_factory = lambda: sessions

uvicorn.run(app, host="0.0.0.0", port=8000)
