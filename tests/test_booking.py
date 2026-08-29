from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.models import Customer


def booking_payload(
    seed_ids, email="minh@example.com", start="2026-09-01T08:00:00+07:00"
):
    return {
        "dealership_id": seed_ids["dealership_id"],
        "service_type_id": seed_ids["oil_change_id"],
        "start_time": start,
        "customer": {
            "full_name": "Minh Nguyen",
            "email": email,
            "phone": "+84901234567",
        },
        "vehicle": {"make": "Toyota", "model": "Corolla", "year": 2020},
    }


async def test_booking_happy_path(client, seed_ids):
    """A valid booking is confirmed with correct times and customer/vehicle details."""
    response = await client.post("/api/appointments", json=booking_payload(seed_ids))
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "confirmed"
    assert body["customer"]["email"] == "minh@example.com"
    assert body["vehicle"]["make"] == "Toyota"

    start = datetime.fromisoformat(body["start_time"])
    end = datetime.fromisoformat(body["end_time"])
    assert start == datetime(2026, 9, 1, 1, 0, tzinfo=UTC)
    assert end - start == timedelta(minutes=60)


async def test_booking_exhausts_capacity_then_conflicts(client, seed_ids):
    """An additional booking at an already-full slot is rejected with a capacity error."""
    for i in range(3):
        payload = booking_payload(
            seed_ids,
            email=f"customer{i}@example.com",
            start="2026-09-01T08:00:00+07:00",
        )
        payload["service_type_id"] = seed_ids["full_service_id"]
        response = await client.post("/api/appointments", json=payload)
        assert response.status_code == 201, response.text

    payload = booking_payload(
        seed_ids,
        email="overflow@example.com",
        start="2026-09-01T08:00:00+07:00",
    )
    payload["service_type_id"] = seed_ids["full_service_id"]
    response = await client.post("/api/appointments", json=payload)
    assert response.status_code == 409
    assert response.json()["code"] in {
        "no_free_bay",
        "no_free_technician",
        "no_capacity",
    }


async def test_booking_unqualified_technician(client, seed_ids):
    """A service with no qualified technician is rejected."""
    payload = booking_payload(seed_ids)
    payload["service_type_id"] = seed_ids["diagnostics_id"]
    response = await client.post("/api/appointments", json=payload)
    assert response.status_code == 409
    assert response.json()["code"] == "no_qualified_technician"


async def test_booking_off_grid_rejected(client, seed_ids):
    """A start time not aligned to the booking grid is rejected."""
    response = await client.post(
        "/api/appointments",
        json=booking_payload(seed_ids, start="2026-09-01T08:15:00+07:00"),
    )
    assert response.status_code == 422
    assert "grid" in response.json()["detail"]


async def test_booking_outside_business_hours_rejected(client, seed_ids):
    """A start time outside business hours is rejected."""
    response = await client.post(
        "/api/appointments",
        json=booking_payload(seed_ids, start="2026-09-01T18:00:00+07:00"),
    )
    assert response.status_code == 422
    assert "outside business hours" in response.json()["detail"]


async def test_booking_on_sunday_allowed(client, seed_ids):
    """Sunday uses the same hours as every other day, so a daytime booking works."""
    response = await client.post(
        "/api/appointments",
        json=booking_payload(seed_ids, start="2026-08-30T08:00:00+07:00"),  # Sunday
    )
    assert response.status_code == 201, response.text


async def test_booking_invalid_email_rejected(client, seed_ids):
    """A malformed customer email fails validation."""
    payload = booking_payload(seed_ids)
    payload["customer"]["email"] = "not-an-email"
    response = await client.post("/api/appointments", json=payload)
    assert response.status_code == 422


async def test_booking_unknown_dealership(client, seed_ids):
    """Booking at a nonexistent dealership returns 404."""
    payload = booking_payload(seed_ids)
    payload["dealership_id"] = 9999
    response = await client.post("/api/appointments", json=payload)
    assert response.status_code == 404


async def test_booking_reuses_customer_by_email(client, seed_ids, db_session):
    """Repeat bookings with the same email reuse the existing customer instead of creating a new one."""
    first = await client.post(
        "/api/appointments",
        json=booking_payload(seed_ids, start="2026-09-01T08:00:00+07:00"),
    )
    second = await client.post(
        "/api/appointments",
        json=booking_payload(seed_ids, start="2026-09-01T09:00:00+07:00"),
    )
    assert first.status_code == 201
    assert second.status_code == 201

    count = await db_session.scalar(select(func.count()).select_from(Customer))
    assert count == 1


async def test_booking_unknown_service_type(client, seed_ids):
    """Booking a nonexistent service type returns 404."""
    payload = booking_payload(seed_ids)
    payload["service_type_id"] = 9999
    response = await client.post("/api/appointments", json=payload)
    assert response.status_code == 404


async def test_booking_invalid_vehicle_rejected(client, seed_ids):
    """A vehicle year outside the allowed range fails validation."""
    payload = booking_payload(seed_ids)
    payload["vehicle"]["year"] = 1800
    response = await client.post("/api/appointments", json=payload)
    assert response.status_code == 422


async def test_booking_missing_customer_rejected(client, seed_ids):
    """A booking without customer details fails validation."""
    payload = booking_payload(seed_ids)
    del payload["customer"]
    response = await client.post("/api/appointments", json=payload)
    assert response.status_code == 422


async def test_booking_naive_datetime_assumed_utc(client, seed_ids):
    """A naive start time is treated as UTC (01:00 UTC = 08:00 dealership local)."""
    response = await client.post(
        "/api/appointments",
        json=booking_payload(seed_ids, start="2026-09-01T01:00:00"),
    )
    assert response.status_code == 201, response.text
    start = datetime.fromisoformat(response.json()["start_time"])
    assert start == datetime(2026, 9, 1, 1, 0, tzinfo=UTC)


async def test_booking_end_of_day_rejected(client, seed_ids):
    """A booking whose end time passes closing time is rejected."""
    response = await client.post(
        "/api/appointments",
        json=booking_payload(seed_ids, start="2026-09-01T17:00:00+07:00"),
    )
    assert response.status_code == 422
    assert "outside business hours" in response.json()["detail"]
