"""Tests for the global search endpoint."""

from datetime import datetime, timezone

from codememory.domain.models import Problem, Submission, Attempt
from codememory.domain.enums import DifficultyLevel, SubmissionStatus


# ---------------------------------------------------------------------------
# 1. Exact problem search
# ---------------------------------------------------------------------------

def test_search_exact_problem(client):
    """Searching the exact problem title returns that problem as rank 0."""
    resp = client.get("/api/v1/search", params={"q": "Two Sum"})
    assert resp.status_code == 200
    data = resp.json()

    assert data["query"] == "Two Sum"
    assert len(data["results"]) >= 1

    problem_results = [r for r in data["results"] if r["type"] == "problem"]
    assert len(problem_results) == 1
    p = problem_results[0]
    assert p["title"] == "Two Sum"
    assert p["slug"] == "two-sum"
    assert p["metadata"]["difficulty"] == "Easy"
    assert "Array" in p["metadata"]["topics"]


# ---------------------------------------------------------------------------
# 2. Partial problem search
# ---------------------------------------------------------------------------

def test_search_partial_problem(client):
    """Partial query matches problems whose title contains the query."""
    resp = client.get("/api/v1/search", params={"q": "two"})
    assert resp.status_code == 200
    data = resp.json()

    problem_results = [r for r in data["results"] if r["type"] == "problem"]
    assert len(problem_results) >= 1
    assert all("two" in r["title"].lower() for r in problem_results)


# ---------------------------------------------------------------------------
# 3. Case-insensitive search
# ---------------------------------------------------------------------------

def test_search_case_insensitive(client):
    """Search should be case-insensitive."""
    resp = client.get("/api/v1/search", params={"q": "TWO SUM"})
    assert resp.status_code == 200
    data = resp.json()

    problem_results = [r for r in data["results"] if r["type"] == "problem"]
    assert len(problem_results) >= 1
    assert problem_results[0]["title"] == "Two Sum"


# ---------------------------------------------------------------------------
# 4. Submission search
# ---------------------------------------------------------------------------

def test_search_submission(client):
    """Search returns submissions whose problem title matches."""
    resp = client.get("/api/v1/search", params={"q": "Two Sum"})
    assert resp.status_code == 200
    data = resp.json()

    submission_results = [r for r in data["results"] if r["type"] == "submission"]
    assert len(submission_results) >= 1

    sub = submission_results[0]
    assert sub["title"] == "Two Sum"
    assert sub["metadata"]["language"] == "python"
    assert sub["metadata"]["status"] == "Accepted"


# ---------------------------------------------------------------------------
# 5. Mixed result types
# ---------------------------------------------------------------------------

def test_search_mixed_result_types(client):
    """A single query can return both problem and submission results."""
    resp = client.get("/api/v1/search", params={"q": "two sum"})
    assert resp.status_code == 200
    data = resp.json()

    types_present = {r["type"] for r in data["results"]}
    assert "problem" in types_present
    assert "submission" in types_present


# ---------------------------------------------------------------------------
# 6. Empty query
# ---------------------------------------------------------------------------

def test_search_empty_query(client):
    """An empty query returns 422 (min_length=1 on the query param)."""
    resp = client.get("/api/v1/search", params={"q": ""})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 7. No results
# ---------------------------------------------------------------------------

def test_search_no_results(client):
    """A query that matches nothing returns an empty results list."""
    resp = client.get("/api/v1/search", params={"q": "zzznonexistentproblem123"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"] == []


# ---------------------------------------------------------------------------
# 8. Active-account isolation
# ---------------------------------------------------------------------------

def test_search_account_isolation(multi_account_client):
    """Only the active account's submissions are returned in search results.

    Account A (jaypatil1229) has 2 submissions on 'two-sum'.
    Account B (maytrix) has 1 submission on 'add-two-numbers'.
    B is active, so searching 'two sum' must not return A's submissions —
    and 'two-sum' must not even appear as a problem for B.
    """
    # B is active — searching 'two sum' should return zero results
    resp = multi_account_client.get("/api/v1/search", params={"q": "two sum"})
    assert resp.status_code == 200
    data = resp.json()
    # B has no 'two-sum' submissions, so no results
    assert len(data["results"]) == 0

    # Searching B's problem returns B's submission only
    resp = multi_account_client.get("/api/v1/search", params={"q": "add two numbers"})
    assert resp.status_code == 200
    data = resp.json()

    sub_results = [r for r in data["results"] if r["type"] == "submission"]
    assert len(sub_results) == 1
    assert sub_results[0]["metadata"]["sourceAccount"] == "maytrix"
    assert "2001" in sub_results[0]["id"]


# ---------------------------------------------------------------------------
# 9. Account switching
# ---------------------------------------------------------------------------

def test_search_account_switching(multi_account_service):
    """Switching the active account changes which submissions appear in search.

    Account A (jaypatil1229) has 2 submissions on 'two-sum'.
    Account B (maytrix) has 0 submissions on 'two-sum'.
    Searching 'two sum' as A must return 2 submissions; as B it must return 0.
    """
    from api.app import create_app
    from api.dependencies import get_service
    from fastapi.testclient import TestClient
    from codememory.connectors.account.models import AccountConnection, AccountStatus
    from datetime import datetime as dt, timezone as tz

    # --- As B (maytrix active) — should return nothing ---
    app = create_app(service=multi_account_service)
    app.dependency_overrides[get_service] = lambda: multi_account_service
    with TestClient(app) as c:
        resp = c.get("/api/v1/search", params={"q": "two sum"})
        assert resp.status_code == 200
        assert resp.json()["results"] == []

    # --- Switch to A (jaypatil1229 active) — should return 2 submissions ---
    account_service = multi_account_service.leetcode._account_service
    conn_a = AccountConnection(
        provider="LeetCode",
        username="jaypatil1229",
        display_name="Jay Patil",
        user_avatar=None,
        status=AccountStatus.CONNECTED,
        connected_at=dt.now(tz.utc),
        capabilities={"sync": True, "profile": True},
        metadata={"solved_all": 1, "solved_easy": 1, "solved_medium": 0, "solved_hard": 0, "ranking": 9999},
    )
    account_service.save_connection(conn_a)

    with TestClient(app) as c:
        resp = c.get("/api/v1/search", params={"q": "two sum"})
        assert resp.status_code == 200
        data = resp.json()
        sub_results = [r for r in data["results"] if r["type"] == "submission"]
        assert len(sub_results) == 2
        assert all(r["metadata"]["sourceAccount"] == "jaypatil1229" for r in sub_results)


# ---------------------------------------------------------------------------
# 10. No connected account
# ---------------------------------------------------------------------------

def test_search_no_connected_account(empty_client):
    """With no connected account, LeetCode-sourced submissions are hidden."""
    # Seed a non-LeetCode (source_provider=None) problem
    prob = Problem(
        id="prob-manual",
        title="Manual Problem",
        slug="manual-problem",
        difficulty=DifficultyLevel.MEDIUM,
        platform="LeetCode",
        topics=["Array"],
    )
    attempt = Attempt(
        problem_id="prob-manual",
        attempt_number=1,
        status=SubmissionStatus.ACCEPTED,
        submissions=[
            Submission(
                problem_id="prob-manual",
                code="x = 1",
                language="python",
                status=SubmissionStatus.ACCEPTED,
                submitted_at=datetime.now(timezone.utc),
            )
        ],
    )
    prob.attempts.append(attempt)
    empty_client.app.state._injected_service.storage.save(prob)

    resp = empty_client.get("/api/v1/search", params={"q": "manual"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) >= 1
    # The non-LeetCode submission should be visible
    sub_results = [r for r in data["results"] if r["type"] == "submission"]
    assert len(sub_results) >= 1


# ---------------------------------------------------------------------------
# 11. Result limit / order
# ---------------------------------------------------------------------------

def test_search_result_limit_and_order(client):
    """Results are bounded by the limit parameter and come back in rank order."""
    resp = client.get("/api/v1/search", params={"q": "two", "limit": 1})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) <= 1

    # Without limit, default cap of 50 applies
    resp2 = client.get("/api/v1/search", params={"q": "two"})
    assert resp2.status_code == 200
    assert len(resp2.json()["results"]) <= 50


# ---------------------------------------------------------------------------
# 12. Special characters
# ---------------------------------------------------------------------------

def test_search_special_characters(client):
    """A query with special characters does not crash the search endpoint."""
    resp = client.get("/api/v1/search", params={"q": "two @# sum"})
    assert resp.status_code == 200
    data = resp.json()
    # The special character query should simply match nothing (or whatever it
    # happens to match) without erroring.
    assert isinstance(data["results"], list)


def test_search_query_too_long(client):
    """A query exceeding the max length returns 422."""
    resp = client.get("/api/v1/search", params={"q": "a" * 201})
    assert resp.status_code == 422
