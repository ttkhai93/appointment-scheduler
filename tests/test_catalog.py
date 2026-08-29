async def test_dealerships(client):
    response = await client.get("/api/dealerships")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["timezone"] == "Asia/Ho_Chi_Minh"


async def test_service_types(client, seed_ids):
    response = await client.get("/api/service-types")
    assert response.status_code == 200
    service_types = {item["name"]: item for item in response.json()}
    assert service_types["Oil Change"]["duration_minutes"] == 60
    assert service_types["Full Service"]["duration_minutes"] == 120


async def test_technicians_with_qualifications(client, seed_ids):
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
    response = await client.get(
        f"/api/service-bays?dealership_id={seed_ids['dealership_id']}"
    )
    assert response.status_code == 200
    assert len(response.json()) == 3
