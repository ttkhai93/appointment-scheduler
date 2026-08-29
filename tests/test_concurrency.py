import asyncio


def _payload(seed_ids, email, start="2026-09-01T08:00:00+07:00"):
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


async def test_concurrent_double_booking_exactly_one_wins(client, seed_ids):
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


async def test_concurrent_full_capacity_bookings(client, seed_ids):
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
        for i in range(4)
    ]
    responses = await asyncio.gather(
        *(client.post("/api/appointments", json=p) for p in payloads)
    )
    statuses = sorted(r.status_code for r in responses)
    assert statuses == [201, 201, 201, 409]
