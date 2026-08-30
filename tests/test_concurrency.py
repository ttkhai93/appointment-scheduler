import asyncio

from sqlalchemy import select

from app.models import Appointment


def _payload(
    seed_ids,
    email,
    start="2026-09-01T08:00:00+07:00",
    service_type_id=None,
):
    return {
        "dealership_id": seed_ids["dealership_id"],
        "service_type_id": service_type_id or seed_ids["oil_change_id"],
        "start_time": start,
        "customer": {
            "full_name": f"Customer {email}",
            "email": email,
            "phone": "+84901234567",
        },
        "vehicle": {"make": "Toyota", "model": "Corolla"},
    }


async def test_concurrent_double_booking_exactly_one_wins(client, seed_ids):
    """With one slot left, concurrent duplicate bookings yield exactly one success and one conflict."""
    # Pre-book 2 of the 3 bays at the same slot so exactly one of the
    # concurrent requests can win.
    for email in ("pre1@example.com", "pre2@example.com"):
        response = await client.post(
            "/api/appointments", json=_payload(seed_ids, email)
        )
        assert response.status_code == 201, response.text

    responses = await asyncio.gather(
        client.post(
            "/api/appointments",
            json=_payload(seed_ids, "race1@example.com"),
        ),
        client.post(
            "/api/appointments",
            json=_payload(seed_ids, "race2@example.com"),
        ),
    )
    statuses = sorted(r.status_code for r in responses)
    assert statuses == [201, 409]
    conflict = next(r for r in responses if r.status_code == 409)
    assert conflict.json()["code"] in {
        "no_free_bay",
        "no_free_technician",
        "no_capacity",
    }


async def test_concurrent_full_capacity_bookings_all_succeed_with_max_booking_attempts(
    client, seed_ids, db_session
):
    """Concurrent requests can fill all capacity, with every booking succeeding."""
    payloads = [
        {
            "dealership_id": seed_ids["dealership_id"],
            "service_type_id": seed_ids["full_service_id"],
            "start_time": "2026-09-01T08:00:00+07:00",
            "customer": {
                "full_name": f"Customer {i}",
                "email": f"race{i}@example.com",
                "phone": "+84901234567",
            },
            "vehicle": {"make": "Toyota", "model": "Corolla"},
        }
        for i in range(3)
    ]
    responses = await asyncio.gather(
        *(client.post("/api/appointments", json=p) for p in payloads)
    )
    statuses = sorted(r.status_code for r in responses)
    assert statuses == [201, 201, 201]

    rows = list((await db_session.scalars(select(Appointment))).all())
    assert len(rows) == 3
    assert all(a.status == "confirmed" for a in rows)
    assert len({a.technician_id for a in rows}) == 3
    assert len({a.service_bay_id for a in rows}) == 3


async def test_concurrent_technician_limited_capacity_overflow_rejected(
    client, seed_ids, db_session
):
    """Tire rotation has 2 qualified techs for 3 bays; the overflow booking is rejected."""
    responses = await asyncio.gather(
        *(
            client.post(
                "/api/appointments",
                json=_payload(
                    seed_ids,
                    f"tech-race{i}@example.com",
                    service_type_id=seed_ids["tire_rotation_id"],
                ),
            )
            for i in range(3)
        )
    )
    statuses = sorted(r.status_code for r in responses)
    assert statuses == [201, 201, 409]
    conflict = next(r for r in responses if r.status_code == 409)
    assert conflict.json()["code"] == "no_free_technician"

    rows = list((await db_session.scalars(select(Appointment))).all())
    assert len(rows) == 2
    assert len({a.technician_id for a in rows}) == 2


async def test_concurrent_cross_service_type_overlap_race(client, seed_ids, db_session):
    """A 120-min booking at 08:00 blocks bays/techs for a 60-min booking at 09:00."""
    payloads = [
        _payload(
            seed_ids,
            f"cross-a{i}@example.com",
            start="2026-09-01T08:00:00+07:00",
            service_type_id=seed_ids["full_service_id"],
        )
        for i in range(2)
    ] + [
        _payload(
            seed_ids,
            f"cross-b{i}@example.com",
            start="2026-09-01T09:00:00+07:00",
            service_type_id=seed_ids["oil_change_id"],
        )
        for i in range(2)
    ]
    responses = await asyncio.gather(
        *(client.post("/api/appointments", json=p) for p in payloads)
    )
    statuses = sorted(r.status_code for r in responses)
    assert statuses == [201, 201, 201, 409]
    conflict = next(r for r in responses if r.status_code == 409)
    assert conflict.json()["code"] in {
        "no_free_bay",
        "no_free_technician",
        "no_capacity",
    }

    rows = list((await db_session.scalars(select(Appointment))).all())
    assert len(rows) == 3
    assert len({a.technician_id for a in rows}) == 3
    assert len({a.service_bay_id for a in rows}) == 3
