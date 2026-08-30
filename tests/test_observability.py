import re


async def _metric_value(client, name: str) -> int:
    response = await client.get("/metrics")
    assert response.status_code == 200
    match = re.search(rf"^{name} ([\d.]+)$", response.text, re.MULTILINE)
    assert match, f"metric {name!r} not found in /metrics"
    return int(float(match.group(1)))


async def test_metrics_endpoint_exposes_observability_metrics(client):
    """The /metrics endpoint exposes request and booking-conflict metrics."""
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text
    assert "http_request_duration_seconds" in response.text
    assert "booking_conflicts_total" in response.text


async def test_responses_carry_request_id(client):
    """Every measured response carries an X-Request-ID header."""
    response = await client.get("/health")
    assert response.headers.get("X-Request-ID")


async def test_booking_conflict_increments_counter(client, seed_ids):
    """A rejected booking increments the conflict counter."""
    before = await _metric_value(client, "booking_conflicts_total")

    payload = {
        "dealership_id": seed_ids["dealership_id"],
        "service_type_id": seed_ids["diagnostics_id"],
        "start_time": "2026-09-01T08:00:00+07:00",
        "customer": {
            "full_name": "Minh Nguyen",
            "email": "minh@example.com",
            "phone": "+84901234567",
        },
        "vehicle": {"make": "Toyota", "model": "Corolla", "year": 2020},
    }
    response = await client.post("/api/appointments", json=payload)
    assert response.status_code == 409

    after = await _metric_value(client, "booking_conflicts_total")
    assert after == before + 1
