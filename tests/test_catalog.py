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
