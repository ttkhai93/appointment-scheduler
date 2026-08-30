# Appointment Scheduler

Booking service for vehicle dealerships. A customer requests an appointment
(vehicle + service type + dealership + start time). The service confirms it
only when **both** a service bay and a **qualified** technician are free for
the whole duration, then saves the appointment.

- **Backend**: Python 3.14, FastAPI, SQLAlchemy 2 (async) + asyncpg, PostgreSQL 16
- **Migrations**: Alembic
- **Quality**: pytest, ruff + pre-commit

See [docs/design.md](docs/design.md) for the full system design: architecture,
data model, concurrency strategy, and assumptions.

## Quickstart

Prerequisites: [uv](https://docs.astral.sh/uv/), Docker, and a running Docker daemon.

```bash
make init        # uv sync + install pre-commit hooks
make up          # docker compose up -d --wait postgres
make db-upgrade  # apply Alembic migrations
make seed        # idempotent seed data (1 dealership, 5 services, 4 techs, 3 bays)
make dev         # uvicorn on http://localhost:8000
make monitoring  # Prometheus + Grafana with a provisioned dashboard
```

Interactive API docs at http://localhost:8000/docs

## Observability

- `GET /metrics` — Prometheus metrics (request count, latency, booking conflicts).
- `make monitoring` — starts Prometheus (http://localhost:9090) and Grafana
  (http://localhost:3000, anonymous viewer). Grafana auto-loads the
  "Appointment Scheduler" dashboard: request rate, p95 latency, and booking
  conflicts. Prometheus scrapes the app at `host.docker.internal:8000`, so run
  `make dev` first.

## Booking flow (interactive)

Try the booking flow end to end in the interactive API docs (Swagger UI) at
http://localhost:8000/docs, in this order:

1. `GET /api/dealerships` and `GET /api/service-types` to look up the
   reference data you need to book (dealership and service type IDs).
2. `POST /api/appointments` to book (customer and vehicle are
   upserted atomically with the appointment).
3. `GET /api/appointments/{id}` to retrieve the appointment.

Expect `201` with the confirmed appointment (customer, vehicle, technician, and
service bay), `409` when no qualified technician or free bay exists, or `422`
when the request violates domain rules (off-grid, outside business hours).

Business hours are global configuration — every dealership is open the same
hours every day (default 08:00–17:30 local, configurable via
`BUSINESS_OPEN_TIME` / `BUSINESS_CLOSE_TIME`).

## Testing

```bash
make test   # starts Postgres (compose) and runs the full pytest suite
```

The suite runs against a real PostgreSQL database and covers: happy-path
booking, capacity exhaustion, unqualified technicians, off-grid/out-of-hours
rejection, boundary adjacency, concurrent double-booking (exactly one winner),
DB-level exclusion constraints, and persistence across sessions.

## Project layout

```text
alembic/                 # migrations (initial schema + exclusion constraints)
app/
  api/                   # HTTP routes (health, catalog, appointments)
  services/              # booking + availability business logic, time utilities
  config.py              # pydantic-settings
  database.py            # async engine / session
  models.py              # SQLAlchemy models
  schemas.py             # Pydantic request/response models
  seed.py                # idempotent seed data
  application.py         # FastAPI factory
tests/                   # unit + integration tests (real Postgres)
docs/design.md           # system design document
infrastructures/telemetry/  # Prometheus + Grafana configs (provisioned dashboard)
main.py                  # uvicorn entrypoint
```

## Make targets

```text
init         install dependencies + pre-commit hooks
up           start Postgres
dev          run the API with reload
test         run pytest (starts Postgres)
db-upgrade   apply Alembic migrations
seed         load seed data
monitoring   start Prometheus + Grafana (provisioned dashboard)
lint         ruff check --fix + format
fmt          ruff format
```
