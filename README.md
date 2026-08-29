# Appointment Scheduler

A resource-constrained appointment booking service for vehicle service
dealerships. Customers request a service appointment for a vehicle, service
type, and dealership; the service verifies that **both** a service bay and a
**qualified** technician are free for the entire duration, then persists a
confirmed appointment.

- **Backend**: Python 3.14, FastAPI, SQLAlchemy 2 (async) + asyncpg, PostgreSQL 16
- **Migrations**: Alembic
- **Quality**: pytest, ruff + pre-commit

See [docs/design.md](docs/design.md) for the full system design, including the
architecture diagram, data model, concurrency strategy, and recorded
assumptions.

## Quickstart

Prerequisites: [uv](https://docs.astral.sh/uv/), Docker, and a running Docker
daemon.

```bash
make init        # uv sync + install pre-commit hooks
make up          # docker compose up -d --wait postgres
make db-upgrade  # apply Alembic migrations
make seed        # idempotent seed data (1 dealership, 5 services, 4 techs, 3 bays)
make dev         # uvicorn on http://localhost:8000
```

Interactive API docs: http://localhost:8000/docs

## Booking flow (interactive)

Walk through the booking flow end to end in the interactive API docs
(Swagger UI) at http://localhost:8000/docs, in this order:

1. `GET /api/dealerships`, `GET /api/service-types`, and
   `GET /api/technicians?dealership_id=1` to look up reference data.
2. `GET /api/availability?dealership_id=1&service_type_id=1&date=2026-09-01`
   to check slots for a date (60-minute grid, interpreted in the dealership's
   timezone), or `GET /api/availability/check` to verify a specific start time
   in real time.
3. `POST /api/appointments` to book (customer and vehicle are
   created/upserted atomically with the appointment).
4. `GET /api/appointments/{id}` to retrieve the appointment.

Expect `201` with the confirmed appointment (customer, vehicle, technician, and
service bay), `409` when no qualified technician / free bay exists, or `422`
when the request violates domain rules (off-grid, outside business hours,
closed day).

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
  api/                   # HTTP routes (health, catalog, availability, appointments)
  services/              # booking + availability business logic, time utilities
  config.py              # pydantic-settings
  database.py            # async engine / session
  models.py              # SQLAlchemy models
  schemas.py             # Pydantic request/response models
  seed.py                # idempotent seed data
  application.py         # FastAPI factory
tests/                   # unit + integration tests (real Postgres)
docs/design.md           # system design document
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
lint         ruff check --fix + format
fmt          ruff format
```
