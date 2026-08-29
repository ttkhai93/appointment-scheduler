async def test_dealerships(client):
    """Seeded dealership is listed with its configured timezone."""
    response = await client.get("/api/dealerships")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["timezone"] == "Asia/Ho_Chi_Minh"


async def test_service_types(client, seed_ids):
    """Catalog exposes seeded service types with their configured durations."""
    response = await client.get("/api/service-types")
    assert response.status_code == 200
    service_types = {item["name"]: item for item in response.json()}
    assert service_types["Oil Change"]["duration_minutes"] == 60
    assert service_types["Full Service"]["duration_minutes"] == 120


async def test_technicians_with_qualifications(client, seed_ids):
    """Technician list includes seeded technicians and their qualifications."""
    response = await client.get(
        f"/api/technicians?dealership_id={seed_ids['dealership_id']}"
    )
    assert response.status_code == 200
    technicians = response.json()
    assert len(technicians) == 4
    oil_id = seed_ids["oil_change_id"]
    oil_qualified = [t for t in technicians if oil_id in t["qualification_ids"]]
    assert len(oil_qualified) >= 2


async def test_service_bays(client, seed_ids):
    """Dealership exposes its three seeded service bays."""
    response = await client.get(
        f"/api/service-bays?dealership_id={seed_ids['dealership_id']}"
    )
    assert response.status_code == 200
    assert len(response.json()) == 3


async def test_technician_qualifications(client, seed_ids):
    """Qualification endpoint returns complete technician/service-type pairs."""
    response = await client.get(
        f"/api/technician-qualifications?dealership_id={seed_ids['dealership_id']}"
    )
    assert response.status_code == 200
    qualifications = response.json()
    oil_id = seed_ids["oil_change_id"]
    assert any(q["service_type_id"] == oil_id for q in qualifications)
    for q in qualifications:
        assert q["technician_id"]
        assert q["technician_name"]
        assert q["service_type_id"]
        assert q["service_type_name"]


async def test_catalog_unknown_dealership_returns_empty(client):
    """Catalog endpoints filter to empty lists for a nonexistent dealership."""
    for path in (
        "/api/technicians",
        "/api/service-bays",
        "/api/technician-qualifications",
    ):
        response = await client.get(path, params={"dealership_id": 9999})
        assert response.status_code == 200
        assert response.json() == []


async def test_catalog_invalid_dealership_id_rejected(client):
    """Catalog endpoints reject a non-integer dealership_id with 422."""
    for path in (
        "/api/technicians",
        "/api/service-bays",
        "/api/technician-qualifications",
    ):
        response = await client.get(path, params={"dealership_id": "abc"})
        assert response.status_code == 422
