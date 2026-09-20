def test_list_problems(client):
    response = client.get("/api/v1/problems")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "page" in data
    assert "pageSize" in data
    assert "total" in data
    
    assert data["total"] == 1
    assert data["items"][0]["slug"] == "two-sum"
    # Ensure nested attempts are omitted from list view
    assert "attempts" not in data["items"][0]

def test_list_problems_filter_search(client):
    response = client.get("/api/v1/problems?search=unknown")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0

def test_get_problem(client):
    response = client.get("/api/v1/problems/two-sum")
    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "two-sum"
    assert "attempts" in data
    assert len(data["attempts"]) == 1

def test_get_problem_not_found(client):
    response = client.get("/api/v1/problems/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND" # or whatever the global handler gives


def test_get_problem_concurrent(client):
    # The frontend fetches problem details concurrently. Every request shares
    # one pooled DuckDB connection; without serialisation, a statement from one
    # thread resets another's pending result set and rows are mixed across
    # threads — which is how ``attempt_number`` ended up validating the slug.
    # Twenty identical requests must all succeed with the correct body.
    from concurrent.futures import ThreadPoolExecutor

    slug = "two-sum"
    with ThreadPoolExecutor(max_workers=20) as pool:
        responses = list(pool.map(lambda _: client.get(f"/api/v1/problems/{slug}"), range(20)))

    assert len(responses) == 20
    for response in responses:
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["slug"] == slug
        assert len(body["attempts"]) == 1
        assert body["attempts"][0]["attemptNumber"] == 1
        assert body["attempts"][0]["submissions"]
