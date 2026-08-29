async def test_health(client):
    """Health endpoint reports the service and database as healthy."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database"] == "ok"


async def test_health_database_unreachable(client, monkeypatch):
    """Health endpoint reports the database as unreachable when the DB check fails."""

    async def broken_database_check(session):
        return False

    monkeypatch.setattr("app.api.health.check_database", broken_database_check)
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database"] == "unreachable"
