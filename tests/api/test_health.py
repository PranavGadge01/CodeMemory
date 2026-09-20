def test_health_check(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "overall" in data
    assert data["overall"] == "ok"
    assert "storage" in data
    assert "timestamp" in data
