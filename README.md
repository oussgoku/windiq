# WindIQ

[Live demo](https://34.32.49.87.sslip.io/) · [Public health](https://34.32.49.87.sslip.io/health/ingestion)

WindIQ ingests hourly mast measurements and estimates wind-turbine energy. A
FastAPI service serves both the JSON API and a small browser dashboard; a
separate worker keeps the measurements up to date.

## Run locally

Copy `.env.example` to `.env`. Set `POSTGRES_PASSWORD` to a random hex string
(for example, from `openssl rand -hex 24`), then set the upstream API URL, client
ID, and secret. Keep `.env` out of Git.

```sh
docker compose up -d db
docker compose run --rm api alembic upgrade head
docker compose up -d api scheduler
```

Open <http://localhost:8000>. The worker ingests immediately and then on each
hourly boundary. Both published ports bind to localhost; the database is not
exposed to other machines. To run Python commands on the host, also set
`DATABASE_URL=postgresql+psycopg://windiq:<password>@localhost:5432/windiq`
in `.env` and install Python 3.12 and [uv](https://docs.astral.sh/uv/).

To preview the dashboard layout without API credentials or a database, run
`python3 -m http.server 8001 --directory frontend` and open
<http://localhost:8001/?demo=1>. This mode is clearly labeled and uses sample
figures; the normal app at port 8000 uses live API and database data.

The dashboard opens in German. Use the DE/EN control in the header to switch
languages; the choice is saved in the browser for later visits. The annual cards
show energy calculated from usable measurements in the last 12 months. An
additional gap-adjusted estimate appears in the methodology panel. Collection
status and recent runs refresh every five minutes while the tab is visible,
and the dashboard shows when they were last checked. Displayed timestamps use
`Europe/Berlin` (MEZ/MESZ); calculation windows and API timestamps remain UTC.

To test the frontend and API together without upstream credentials, run
`docker compose -f compose.preview.yaml up -d --build` and open
<http://localhost:8000>. This starts an isolated PostgreSQL test database and
labels the generated data in the dashboard. It does not run the ingestion
worker or use the normal local database. Stop it with
`docker compose -f compose.preview.yaml down`.

## API

| Route | Purpose |
| --- | --- |
| `GET /health` | Process liveness |
| `GET /ready` | Database readiness |
| `GET /health/ingestion` | Latest run and freshness; 503 after a failure or prolonged gap |
| `GET /energy/annual` | Rolling 12-month AEP, P50, P90, and coverage |
| `GET /energy?start=...&end=...` | Observed energy for a selected UTC window |
| `GET /dashboard/context` | Site inputs, recent measurements, and collection status for the dashboard |
| `GET /ingestion/runs?limit=20&before_id=...` | Newest-first stored collection runs, paginated with `next_before_id` |

The annual window ends at the current UTC midnight and starts on the same date
one year earlier. It includes the start and excludes the end. The API reports
observed energy separately from an optional annualized estimate. For that estimate, it
multiplies observed energy by `expected_hours / usable_hours`. This assumes
missing and invalid hours resemble usable hours; low coverage makes the result
less reliable. With no usable hours, the annual estimate is `null`. Monthly
bars show observed energy and are never scaled.

`/energy` accepts timezone-aware timestamps aligned to UTC hours, with a maximum
window of two years. It sums only
usable observations, with no gap filling or annualization. Both energy routes
report expected, observed, and usable hours, exclusions, monthly energy, and a
seven-day wind series with gaps for missing readings.

The calculation adjusts measured speed to hub height using the site shear
exponent, interpolates the turbine power curve, and sums hourly kW as MWh.
P50 applies availability, electrical, and wake losses in sequence. P90 is
`P50 × (1 − 1.282 × uncertainty)`. Source km/h readings are converted to m/s
for calculation only; raw values remain in the database.

## Ingestion and operation

The worker authenticates to the [WindIQ upstream API](https://windiq-mock-api.sliplane.app/docs),
reads paginated measurements, and saves each pass in `ingestion_runs`. It uses
the latest source update time with a one-second overlap so corrected records
are picked up. Measurements and the sync checkpoint commit together after the
last page. Invalid readings are retained and counted, rather than turned into
zero wind speeds.

The dashboard shows the three most recent runs and can page through the full
`ingestion_runs` history. Production PostgreSQL stores that table in the
`postgres_data` Docker volume on the VM disk, so app redeploys and container
restarts keep it. Destroying the VM disk would remove the history; no separate
database backup is configured.

Run one pass with `uv run python -m windiq.ingest`. The scheduler interval
defaults to 3600 seconds. On restart it skips the current interval if that
interval already succeeded, avoiding an extra upstream request during a deploy.
`/health/ingestion` becomes unhealthy when the latest
run fails or the last success is more than 9000 seconds old. Run one scheduler
replica and monitor both `/ready` and `/health/ingestion` from outside the VM.
Apply migrations before starting the API and worker on each release.

The default Compose file is for local use and binds the API to localhost.
The [Google Cloud deployment guide](docs/deployment.md) covers Terraform,
production Compose, HTTPS, VM secrets, and GitHub Actions rollout. Deployment stays
disabled until the VM and repository secrets are configured.

## Checks

```sh
uv sync --frozen
uv run pytest
uv run ruff check .
uv run ruff format --check .
```
