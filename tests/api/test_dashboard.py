def test_get_dashboard(client):
    response = client.get("/api/v1/dashboard")
    assert response.status_code == 200
    data = response.json()
    
    # Assert top-level keys match schema
    expected_keys = {
        "overview", "activity", "timeline", "struggles", 
        "topics", "languages", "difficulties", "revisionQueue", "progress"
    }
    assert set(data.keys()) == expected_keys
    
    # Assert camelCase is applied correctly
    assert "totalProblems" in data["overview"]
    assert data["overview"]["totalProblems"] == 1  # From seed data
    
    # Assert deferred fields are empty lists
    assert data["activity"] == []
    assert data["timeline"] == []
