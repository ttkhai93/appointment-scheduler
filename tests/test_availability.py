from datetime import UTC, datetime


def _booking_payload(seed_ids, email, start="2026-09-01T08:00:00+07:00"):
    return {
        "dealership_id": seed_ids["dealership_id"],
        "service_type_id": seed_ids["oil_change_id"],
        "start_time": start,
        "customer": {
            "full_name": f"Customer {email}",
            "email": email,
            "phone": "+84901234567",
        },
        "vehicle": {"make": "Toyota", "model": "Corolla"},
    }


# ---------------------------------------------------------------------------
# GET /api/availability - free-slot listing
# ---------------------------------------------------------------------------


async def test_availability_lists_free_slots(client, seed_ids):
    """A Tuesday returns nine hourly oil-change slots starting at local opening time."""
    response = await client.get(
        "/api/availability",
        params={
            "dealership_id": seed_ids["dealership_id"],
            "service_type_id": seed_ids["oil_change_id"],
            "date": "2026-09-01",  # Tuesday
        },
    )
    assert response.status_code == 200
    slots = response.json()["slots"]
    assert len(slots) == 9
    first = datetime.fromisoformat(slots[0]["start_time"])
    assert first == datetime(2026, 9, 1, 1, 0, tzinfo=UTC)
    assert datetime.fromisoformat(slots[0]["end_time"]) == datetime(
        2026, 9, 1, 2, 0, tzinfo=UTC
    )


async def test_availability_empty_on_closed_day(client, seed_ids):
    """A day with no business hours (Sunday) returns an empty slot list."""
    response = await client.get(
        "/api/availability",
        params={
            "dealership_id": seed_ids["dealership_id"],
            "service_type_id": seed_ids["oil_change_id"],
            "date": "2026-08-30",  # Sunday
        },
    )
    assert response.status_code == 200
    assert response.json()["slots"] == []


async def test_availability_lists_half_day_saturday_slots(client, seed_ids):
    """A half-day Saturday yields four hourly slots ending at noon local."""
    response = await client.get(
        "/api/availability",
        params={
            "dealership_id": seed_ids["dealership_id"],
            "service_type_id": seed_ids["oil_change_id"],
            "date": "2026-08-29",  # Saturday
        },
    )
    assert response.status_code == 200
    slots = response.json()["slots"]
    assert len(slots) == 4
    assert datetime.fromisoformat(slots[0]["start_time"]) == datetime(
        2026, 8, 29, 1, 0, tzinfo=UTC
    )
    assert datetime.fromisoformat(slots[-1]["start_time"]) == datetime(
        2026, 8, 29, 4, 0, tzinfo=UTC
    )


async def test_availability_unknown_dealership_404(client, seed_ids):
    """Availability for a nonexistent dealership returns 404."""
    response = await client.get(
        "/api/availability",
        params={
            "dealership_id": 9999,
            "service_type_id": seed_ids["oil_change_id"],
            "date": "2026-09-01",
        },
    )
    assert response.status_code == 404


async def test_availability_unknown_service_type_404(client, seed_ids):
    """Availability for a nonexistent service type returns 404."""
    response = await client.get(
        "/api/availability",
        params={
            "dealership_id": seed_ids["dealership_id"],
            "service_type_id": 9999,
            "date": "2026-09-01",
        },
    )
    assert response.status_code == 404


async def test_availability_omits_fully_booked_slot(client, seed_ids):
    """A slot with no free bay/technician pairs is excluded from the listing."""
    for email in ("full1@example.com", "full2@example.com", "full3@example.com"):
        response = await client.post(
            "/api/appointments", json=_booking_payload(seed_ids, email)
        )
        assert response.status_code == 201, response.text

    response = await client.get(
        "/api/availability",
        params={
            "dealership_id": seed_ids["dealership_id"],
            "service_type_id": seed_ids["oil_change_id"],
            "date": "2026-09-01",
        },
    )
    assert response.status_code == 200
    slots = response.json()["slots"]
    assert len(slots) == 8
    first = datetime.fromisoformat(slots[0]["start_time"])
    assert first == datetime(2026, 9, 1, 2, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# GET /api/availability/check - single start-time check
# ---------------------------------------------------------------------------


async def test_availability_check_endpoint(client, seed_ids):
    """The check endpoint reports the Tuesday opening slot as available."""
    params = {
        "dealership_id": seed_ids["dealership_id"],
        "service_type_id": seed_ids["oil_change_id"],
        "start_time": "2026-09-01T08:00:00+07:00",
    }
    check = await client.get("/api/availability/check", params=params)
    assert check.json() == {"available": True, "reason": None}


async def test_availability_check_naive_datetime_assumed_utc(client, seed_ids):
    """A naive start_time is interpreted as UTC by the check endpoint."""
    params = {
        "dealership_id": seed_ids["dealership_id"],
        "service_type_id": seed_ids["oil_change_id"],
        "start_time": "2026-09-01T01:00:00",
    }
    response = await client.get("/api/availability/check", params=params)
    assert response.json() == {"available": True, "reason": None}


async def test_availability_check_still_available_with_partial_capacity(
    client, seed_ids
):
    """The check endpoint stays available while any bay/technician pair remains free."""
    response = await client.post(
        "/api/appointments",
        json=_booking_payload(seed_ids, "partial@example.com"),
    )
    assert response.status_code == 201, response.text

    params = {
        "dealership_id": seed_ids["dealership_id"],
        "service_type_id": seed_ids["oil_change_id"],
        "start_time": "2026-09-01T08:00:00+07:00",
    }
    response = await client.get("/api/availability/check", params=params)
    assert response.json() == {"available": True, "reason": None}


async def test_availability_check_unqualified_service_rejected(client, seed_ids):
    """The check endpoint reports no qualified technician for an unqualified service."""
    params = {
        "dealership_id": seed_ids["dealership_id"],
        "service_type_id": seed_ids["diagnostics_id"],
        "start_time": "2026-09-01T08:00:00+07:00",
    }
    response = await client.get("/api/availability/check", params=params)
    assert response.json() == {"available": False, "reason": "no_qualified_technician"}


async def test_availability_check_busy_technicians_rejected(client, seed_ids):
    """The check endpoint reports no qualified technician when all are busy."""
    for email in ("busy1@example.com", "busy2@example.com", "busy3@example.com"):
        response = await client.post(
            "/api/appointments", json=_booking_payload(seed_ids, email)
        )
        assert response.status_code == 201, response.text

    params = {
        "dealership_id": seed_ids["dealership_id"],
        "service_type_id": seed_ids["oil_change_id"],
        "start_time": "2026-09-01T08:00:00+07:00",
    }
    response = await client.get("/api/availability/check", params=params)
    assert response.json() == {"available": False, "reason": "no_qualified_technician"}


async def test_availability_check_no_free_bay(client, seed_ids):
    """The check endpoint reports no free bay when bays are busy but a technician is free."""
    for email in ("bay1@example.com", "bay2@example.com", "bay3@example.com"):
        payload = _booking_payload(seed_ids, email)
        payload["service_type_id"] = seed_ids["full_service_id"]
        response = await client.post("/api/appointments", json=payload)
        assert response.status_code == 201, response.text

    params = {
        "dealership_id": seed_ids["dealership_id"],
        "service_type_id": seed_ids["oil_change_id"],
        "start_time": "2026-09-01T08:00:00+07:00",
    }
    response = await client.get("/api/availability/check", params=params)
    assert response.json() == {"available": False, "reason": "no_free_bay"}


async def test_availability_check_off_grid_rejected(client, seed_ids):
    """The check endpoint rejects an off-grid start time with 422."""
    params = {
        "dealership_id": seed_ids["dealership_id"],
        "service_type_id": seed_ids["oil_change_id"],
        "start_time": "2026-09-01T08:15:00+07:00",
    }
    response = await client.get("/api/availability/check", params=params)
    assert response.status_code == 422
    assert "grid" in response.json()["detail"]


async def test_availability_check_unknown_dealership_404(client, seed_ids):
    """The check endpoint returns 404 for a nonexistent dealership."""
    params = {
        "dealership_id": 9999,
        "service_type_id": seed_ids["oil_change_id"],
        "start_time": "2026-09-01T08:00:00+07:00",
    }
    response = await client.get("/api/availability/check", params=params)
    assert response.status_code == 404


async def test_availability_check_unknown_service_type_404(client, seed_ids):
    """The check endpoint returns 404 for a nonexistent service type."""
    params = {
        "dealership_id": seed_ids["dealership_id"],
        "service_type_id": 9999,
        "start_time": "2026-09-01T08:00:00+07:00",
    }
    response = await client.get("/api/availability/check", params=params)
    assert response.status_code == 404
