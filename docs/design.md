# Appointment Scheduler — System Design

## 1. Overview

Resource-constrained booking service for vehicle dealerships. A customer
requests an appointment (vehicle + service type + dealership + start time); the
service confirms it only if a **qualified technician** and a **service bay**
are both free for the whole duration, then saves the appointment. Where the
requirements were ambiguous, the agreed decisions are in §3.

## 2. Requirements

1. **Resource-constrained booking** — book a vehicle + service type + dealership at a chosen time.
2. **Real-time availability** — a qualified technician and a service bay must be free for the whole duration.
3. **Confirmed record** — save an appointment linking customer, vehicle, technician, and bay.

## 3. Assumptions (agreed ambiguities)

| # | Decision |
|---|----------|
| A1 | No auth; customer created/upserted by email from the booking payload. |
| A2 | Free-form vehicle fields (make/model/year/VIN); no catalog lookup. |
| A3 | Fixed 60-minute booking grid; duration fixed per service type. |
| A4 | Schema supports many dealerships; one is seeded. |
| A5 | Identical business hours for every dealership, every day of the week (global config: 08:00–17:30 local, same hours all days); local times in the dealership's IANA tz. |
| A6 | No hold step; booking atomically re-checks availability (201 or 409). |
| A7 | Only create/retrieve; reschedule, cancel, and no-show are out of scope. |
| A8 | Bay/technician are busy for the whole appointment; no setup buffers. |
| A9 | Bays/technicians belong to one dealership; no sharing across dealerships. |

## 4. Architecture

**Component roles**

- **API routes (`app/api/`)** — validation (Pydantic), routing, error mapping
  (404/409/422); thin layer, no business logic.
- **Services (`app/services/`)** — availability slot math, qualification/overlap
  checks, and the atomic booking transaction with bounded retry.
- **Data access (`app/models.py`, `app/database.py`)** — ORM models and async
  engine/session management; the typed boundary between services and the store.
- **PostgreSQL** — the database and source of truth; exclusion constraints make
  overlapping bookings impossible at the DB level.
- **Configuration (`app/config.py`)** — settings (DB URL, hours, timezone)
  consumed by the rest of the app.

Schema migrations (Alembic) and the idempotent dev seed script are tooling, not
runtime components; they are covered in §8.

## 5. Data flow

- **Availability lookup** (`GET /api/availability`): date → global business-hours
  grid (60-min slots, dealership tz → UTC) → for each slot, check "any qualified
  technician free?" and "any bay free?" → return free slots. Advisory only;
  booking does the real check.
- **Booking** (`POST /api/appointments`): validate grid + business hours →
  upsert customer/vehicle → check qualifications, free bays, free technicians
  → insert appointment → commit. On an exclusion-constraint race, roll back and
  retry with a fresh snapshot (max 5 attempts) → 201 or 409.
- **Errors**: 404 unknown entity; 422 domain-rule violation (off-grid,
  out-of-hours); 409 no capacity / concurrent loser.

## 6. Data model

| Model | Role |
|-------|------|
| `dealerships` | Venue + IANA timezone; owns bays and technicians. |
| `service_types` | Fixed duration; drives `end_time` and slot grid. |
| `technicians` | Human resource, dealership-scoped. |
| `technician_qualifications` | M2M tech ↔ service type; defines "qualified". |
| `service_bays` | Physical bay, dealership-scoped. |
| `customers` | Contact info; unique email (idempotent upsert). |
| `vehicles` | Free-form car details recorded per appointment. |
| `appointments` | Booking record: customer, vehicle, tech, bay, service type, UTC start/end, status. |

**No-double-booking guarantee**: `EXCLUDE USING gist` on
`(service_bay_id, tstzrange(start_time, end_time))` and
`(technician_id, tstzrange(start_time, end_time))`. `tstzrange` uses `[)`
bounds, so back-to-back appointments are allowed. The service layer adds a
bounded retry so concurrent requests spread across free pairs instead of
failing on the first race.

## 7. API summary

| Method / Path | Purpose |
|---------------|---------|
| GET `/health` | Liveness + DB ping |
| GET `/api/dealerships`, `/api/service-types`, `/api/technicians`, `/api/service-bays`, `/api/technician-qualifications` | Read-only reference data |
| GET `/api/availability?dealership_id&service_type_id&date` | Free slots for a date |
| GET `/api/availability/check?…&start_time` | Advisory check for one time |
| POST `/api/appointments` | Create booking (customer + vehicle + appointment atomically) |
| GET `/api/appointments[/{id}]` | List / retrieve appointments |

Example booking request:

```json
{
  "dealership_id": 1,
  "service_type_id": 1,
  "start_time": "2026-09-01T09:00:00+07:00",
  "customer": { "full_name": "Minh Nguyen", "email": "minh@example.com", "phone": "+84901234567" },
  "vehicle": { "make": "Toyota", "model": "Corolla", "year": 2020, "vin": "JTDBR32E100000001" }
}
```

Timestamps normalize to UTC for storage; responses return UTC.

## 8. Technologies

| Choice | Why |
|--------|-----|
| Python + FastAPI | Requested; async, Pydantic validation, auto OpenAPI. |
| PostgreSQL 16 + asyncpg, SQLAlchemy 2 (async) | Requested; `timestamptz` + `btree_gist` exclusion constraints. |
| Alembic | Versioned, reviewable migrations. |
| uv | Requested; lockfile + managed Python runtime. |
| pytest + pytest-asyncio | Requested; real-Postgres integration tests. |
| Docker Compose | Postgres for local dev and tests. |
| ruff + pre-commit | Requested; lint/format gate on commit. |

Rejected: Redis slot holds (the DB alone guarantees the invariant), app-level
`SELECT … FOR UPDATE` (weaker than exclusion constraints), SQLite (no exclusion
constraints).

## 9. Observability

**Implemented**:

- `/health` — confirms the app is up and the database is reachable.
- **Request logs** — one line per request (request ID, endpoint, status,
  duration); no customer data.
- `/metrics` — Prometheus-format: request count, latency, and booking-conflict
  count.
- **Grafana** — provisioned dashboard (request rate, p95 latency, booking
  conflicts), fed by Prometheus scraping `/metrics`; started via
  `make monitoring` (docker compose).

## 10. GenAI in the design phase

The assistant helped decompose requirements into acceptance criteria, compare
concurrency strategies (exclusion constraints chosen and verified against
Postgres docs), draft the architecture diagram and seed/test designs, and shape
the observability strategy in §9. The test suite and manual cURL checks
verified all suggested code.

## 11. Out of scope

Auth, rescheduling/cancellation/no-shows, VIN/catalog integration, multi-bay
services and shift planning, notifications, deployment of the observability
stack (§9 defines the strategy; tooling lands post-MVP), and horizontal
Postgres scaling.
