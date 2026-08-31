# Appointment Scheduler

A customer requests an appointment with dealership, service type, vehicle,
customer and start time information. The service confirms it only when both a
service bay and a qualified technician are free for the whole duration, then
saves the appointment.

All system details — requirements, architecture, data flow, API contract, and observability — are in [docs/design.md](docs/design.md).

## Quickstart

Prerequisites: Docker and a running Docker daemon. `make init` installs
[uv](https://docs.astral.sh/uv/) automatically if it is not already present.

**Build**

```bash
make init        # uv sync + install pre-commit hooks
make up          # docker compose up -d --wait postgres
make db-upgrade  # apply Alembic migrations
```

**Run**

```bash
make seed        # idempotent seed data (1 dealership, 5 services, 4 techs, 3 bays)
make dev         # uvicorn on http://localhost:8000
```

Interactive API docs at http://localhost:8000/docs

**Automated tests**

```bash
make test        # run the full pytest suite against Postgres
```

**Optional**

```bash
make monitoring  # Prometheus + Grafana with a provisioned dashboard (run `make dev` first)
make lint        # ruff check --fix + format
make fmt         # ruff format
```

## Try it yourself (manual walkthrough)

With the app running (`make dev`) and seeded (`make seed`), open the
interactive API docs at http://localhost:8000/docs and drive the booking flow
in Swagger UI. The examples use dealership 1 and service type 1 (Oil Change,
60 minutes).

**Happy path — confirmed booking**

1. Expand `POST /api/appointments`, click **Try it out**, and paste this
   request body:

```json
{
  "dealership_id": 1,
  "service_type_id": 1,
  "start_time": "2026-09-01T09:00:00+07:00",
  "customer": { "full_name": "Minh Nguyen", "email": "minh@example.com", "phone": "+84901234567" },
  "vehicle": { "make": "Toyota", "model": "Corolla", "year": 2020 }
}
```

2. Click **Execute** — expect `201` with the confirmed appointment (customer,
   vehicle, technician, bay, and UTC times). Note the returned `id`.
3. Expand `GET /api/appointments/{appointment_id}`, click **Try it out**, enter
   that id, and **Execute** — expect `200`.

**Edge cases — validation failures (`422`)**

Repeat the POST with a modified `start_time`:

- `"2026-09-01T09:15:00+07:00"` — off the 60-minute grid → `422`
- `"2026-09-01T18:00:00+07:00"` — outside business hours (closes 17:30) → `422`

**Failure paths — not found and no capacity**

- Set `"dealership_id": 9999` in the body → `404`.
- Set `"start_time": "2026-09-01T10:00:00+07:00"` and **Execute the same POST
  three times** to fill all 3 bays, then a fourth time — the fourth returns
  `409` with code `no_free_technician` (technicians are checked before bays;
  all three qualified technicians and all three bays are taken). The same
  customer email is fine: repeat bookings by one customer are not restricted.

## Project layout

```text
alembic/                    # migrations
app/
  api/                      # HTTP routes
  services/                 # business logic
  config.py                 # configuration
  database.py               # async engine / session
  models.py                 # SQLAlchemy models
  schemas.py                # Pydantic request/response models
  application.py            # FastAPI factory
tests/                      # unit + integration tests (real Postgres)
docs/design.md              # system design document
infrastructures/telemetry/  # Prometheus + Grafana configs (provisioned dashboard)
Makefile                    # setup, run, test, and lint targets
docker-compose.yml          # Postgres + Prometheus + Grafana
pyproject.toml              # project metadata + dependencies (uv)
main.py                     # uvicorn entrypoint
```

## AI Collaboration Narrative

**High-level strategy.**

I provided the information from the Technical Assessment document, ask AI to make a plan for how to implement the feature. But if there are any ambigous requirements, ask me to provide, do not make its own decision.

I review the output, ask some questions, ask to make some changes until everything looks good to me, and approve for it implementation.


**How I verified and refined its output.**
- Every suggested behavior is covered by a integration test. I read the test to verify the test.
- Iterative reviews (can see in the git history):
  + AI add a business_hours table => Removed to reduce complexity, for now.
  + AI add a `vehicles.customer_id` column => Removed to prevent data inconsistency.
  + AI expose API endpoints that user don't use => Removed to reduce complexity
  + AI only test happy path => Added failure-path tests.


**How I ensured final quality.**  

The test suite is the acceptance gate: any
AI-generated change either ships with a passing test or is rejected.
If there are changes to existing test cases, read them carefully to ensure they are valid changes, not to bypass the test.
