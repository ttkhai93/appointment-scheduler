from datetime import UTC, datetime


async def test_availability_lists_free_slots(client, seed_ids):
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


async def test_availability_check_endpoint(client, seed_ids):
    params = {
        "dealership_id": seed_ids["dealership_id"],
        "service_type_id": seed_ids["oil_change_id"],
        "start_time": "2026-09-01T08:00:00+07:00",
    }
    check = await client.get("/api/availability/check", params=params)
    assert check.json() == {"available": True, "reason": None}
