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


def test_problem_detail_account_isolation(multi_account_service):
    """Problem detail endpoint must only return the active account's submissions.

    Account A (jaypatil1229) has submissions on 'two-sum'.
    Account B (maytrix) has a submission on 'add-two-numbers'.
    Only B is active, so 'two-sum' must appear as not-found / empty for B.
    """
    from api.app import create_app
    from api.dependencies import get_service
    from fastapi.testclient import TestClient

    app = create_app(service=multi_account_service)
    app.dependency_overrides[get_service] = lambda: multi_account_service

    with TestClient(app) as client:
        # B is active — 'add-two-numbers' should be visible to B
        resp_b = client.get("/api/v1/problems/add-two-numbers")
        assert resp_b.status_code == 200
        data_b = resp_b.json()
        assert data_b["slug"] == "add-two-numbers"
        assert len(data_b["attempts"]) == 1
        assert len(data_b["attempts"][0]["submissions"]) == 1

        # 'two-sum' belongs to A only — B should NOT see it
        resp_two_sum = client.get("/api/v1/problems/two-sum")
        assert resp_two_sum.status_code == 404

        # Reconnect A as the active account
        from codememory.connectors.account.models import AccountConnection, AccountStatus
        from datetime import datetime, timezone

        account_service = multi_account_service.leetcode._account_service
        conn_a = AccountConnection(
            provider="LeetCode",
            username="jaypatil1229",
            display_name="Jay Patil",
            user_avatar=None,
            status=AccountStatus.CONNECTED,
            connected_at=datetime.now(timezone.utc),
            capabilities={"sync": True, "profile": True},
            metadata={"solved_all": 1, "solved_easy": 1, "solved_medium": 0, "solved_hard": 0, "ranking": 9999},
        )
        account_service.save_connection(conn_a)

        # Now A is active — 'two-sum' should be visible
        resp_a = client.get("/api/v1/problems/two-sum")
        assert resp_a.status_code == 200
        data_a = resp_a.json()
        assert data_a["slug"] == "two-sum"
        # Account A has 2 submissions on two-sum (both accepted)
        total_submissions_a = sum(len(a["submissions"]) for a in data_a["attempts"])
        assert total_submissions_a == 2

        resp_add = client.get("/api/v1/problems/add-two-numbers")
        assert resp_add.status_code == 404


def test_problem_evolution_endpoint(multi_account_service):
    """Solution evolution endpoint returns evolution summary for the active account's problem.

    Account B (maytrix) is active with one submission on 'add-two-numbers'.
    """
    from api.app import create_app
    from api.dependencies import get_service
    from fastapi.testclient import TestClient

    app = create_app(service=multi_account_service)
    app.dependency_overrides[get_service] = lambda: multi_account_service

    with TestClient(app) as client:
        resp = client.get("/api/v1/problems/add-two-numbers/evolution")
        assert resp.status_code == 200
        data = resp.json()
        assert data["problemTitle"] == "Add Two Numbers"


def test_problem_evolution_account_isolation(multi_account_service):
    """Evolution endpoint must only use the active account's submissions.

    With B (maytrix) active, 'two-sum' (A-only) must return 404 for evolution.
    """
    from api.app import create_app
    from api.dependencies import get_service
    from fastapi.testclient import TestClient

    app = create_app(service=multi_account_service)
    app.dependency_overrides[get_service] = lambda: multi_account_service

    with TestClient(app) as client:
        # B is active — 'two-sum' belongs to A only, so evolution must 404
        resp = client.get("/api/v1/problems/two-sum/evolution")
        assert resp.status_code == 404
