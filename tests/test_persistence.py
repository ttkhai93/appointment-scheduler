from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import Appointment


def _payload(seed_ids):
    return {
        "dealership_id": seed_ids["dealership_id"],
        "service_type_id": seed_ids["oil_change_id"],
        "start_time": "2026-09-01T08:00:00+07:00",
        "customer": {
            "full_name": "Minh Nguyen",
            "email": "minh@example.com",
            "phone": "+84901234567",
        },
        "vehicle": {"make": "Toyota", "model": "Corolla", "year": 2020},
    }


async def test_appointment_persists_across_sessions(client, db_session, seed_ids):
    """A booked appointment is persisted with customer, resource assignments, and times."""
    response = await client.post("/api/appointments", json=_payload(seed_ids))
    assert response.status_code == 201
    appointment_id = response.json()["id"]

    appointment = await db_session.scalar(
        select(Appointment)
        .options(selectinload(Appointment.customer))
        .where(Appointment.id == appointment_id)
    )
    assert appointment is not None
    assert appointment.status == "confirmed"
    assert appointment.customer.email == "minh@example.com"
    assert appointment.start_time == datetime.fromisoformat(
        response.json()["start_time"]
    )
    assert appointment.service_bay_id is not None
    assert appointment.technician_id is not None


async def test_appointment_get_and_list(client, seed_ids):
    """Appointments can be fetched by ID and listed by dealership, with 404 for unknown IDs."""
    created = await client.post("/api/appointments", json=_payload(seed_ids))
    appointment_id = created.json()["id"]

    fetched = await client.get(f"/api/appointments/{appointment_id}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == appointment_id
    assert fetched.json()["status"] == "confirmed"

    listing = await client.get(
        "/api/appointments",
        params={"dealership_id": seed_ids["dealership_id"]},
    )
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()] == [appointment_id]

    missing = await client.get("/api/appointments/999999")
    assert missing.status_code == 404


async def test_appointment_list_filters_by_time_and_dealership(client, seed_ids):
    """List endpoint filters appointments by start_from, start_to, and dealership."""
    morning = _payload(seed_ids)
    morning["customer"]["email"] = "morning@example.com"
    first = await client.post("/api/appointments", json=morning)
    assert first.status_code == 201, first.text

    midday = _payload(seed_ids)
    midday["start_time"] = "2026-09-01T09:00:00+07:00"
    midday["customer"]["email"] = "midday@example.com"
    second = await client.post("/api/appointments", json=midday)
    assert second.status_code == 201, second.text

    start_from = await client.get(
        "/api/appointments",
        params={
            "dealership_id": seed_ids["dealership_id"],
            "start_from": "2026-09-01T08:30:00+07:00",
        },
    )
    assert [item["id"] for item in start_from.json()] == [second.json()["id"]]

    start_to = await client.get(
        "/api/appointments",
        params={
            "dealership_id": seed_ids["dealership_id"],
            "start_to": "2026-09-01T08:30:00+07:00",
        },
    )
    assert [item["id"] for item in start_to.json()] == [first.json()["id"]]

    all_appointments = await client.get("/api/appointments")
    assert [item["id"] for item in all_appointments.json()] == [
        first.json()["id"],
        second.json()["id"],
    ]

    unknown_dealership = await client.get(
        "/api/appointments", params={"dealership_id": 9999}
    )
    assert unknown_dealership.status_code == 200
    assert unknown_dealership.json() == []
