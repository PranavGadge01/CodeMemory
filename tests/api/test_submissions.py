"""Tests for the submission detail and list endpoints with account isolation."""

from datetime import datetime, timezone, timedelta
import pytest

from codememory.domain.models import Problem, Submission, Attempt
from codememory.domain.enums import DifficultyLevel, SubmissionStatus


def test_list_submissions_account_scoped(client):
    """The list endpoint must only return the active account's submissions."""
    resp = client.get("/api/v1/submissions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["status"] == "Accepted"


def test_list_submissions_account_isolation(multi_account_service):
    """Only the active account's submissions are returned.

    Account A (jaypatil1229) has 2 submissions on 'two-sum'.
    Account B (maytrix) has 1 submission on 'add-two-numbers'.
    B is active, so only B's submission should be visible.
    """
    from api.app import create_app
    from api.dependencies import get_service
    from fastapi.testclient import TestClient

    app = create_app(service=multi_account_service)
    app.dependency_overrides[get_service] = lambda: multi_account_service

    with TestClient(app) as mc:
        resp = mc.get("/api/v1/submissions")
        assert resp.status_code == 200
        data = resp.json()
        # B (maytrix) is active — only B's 1 submission should be visible
        assert data["total"] == 1
        assert data["summary"]["total"] == 1
        assert data["summary"]["accepted"] == sum(
            item["status"] == "Accepted" for item in data["items"]
        )
        assert data["summary"]["failed"] == data["total"] - data["summary"]["accepted"]
        sub = data["items"][0]
        # B's submission id starts with "leetcode_2001"
        assert "2001" in sub["id"]
        assert sub["sourceAccount"] == "maytrix"


def test_submission_detail_returns_active_account_submission(client):
    """A submission from the active account must be retrievable by ID."""
    resp = client.get("/api/v1/submissions")
    assert resp.status_code == 200
    sub_id = resp.json()["items"][0]["id"]

    resp = client.get(f"/api/v1/submissions/{sub_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == sub_id
    assert data["problemId"] == "mock-1"
    assert data["status"] == "Accepted"
    assert data["language"] == "python"


def test_submission_detail_account_isolation(multi_account_service):
    """A submission from another account must return 404.

    Account A has submission 'leetcode_1001' (source_account=jaypatil1229).
    Account B (maytrix) is active.
    B must not see A's submission.
    """
    from api.app import create_app
    from api.dependencies import get_service
    from fastapi.testclient import TestClient

    app = create_app(service=multi_account_service)
    app.dependency_overrides[get_service] = lambda: multi_account_service

    with TestClient(app) as mc:
        # B is active — should not see A's submission 'leetcode_1001'
        resp = mc.get("/api/v1/submissions/leetcode_1001")
        assert resp.status_code == 404

        # B should see its own submission 'leetcode_2001'
        resp = mc.get("/api/v1/submissions/leetcode_2001")
        assert resp.status_code == 200
        data = resp.json()
        assert "2001" in data["id"]
        assert data["sourceAccount"] == "maytrix"


def test_submission_detail_no_connected_account(empty_client):
    """With no connected account, LeetCode-sourced submissions are hidden."""
    resp = empty_client.get("/api/v1/submissions")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_submission_detail_missing_code(empty_service):
    """A submission with no code must serialize correctly.

    Uses a submission with source_provider=None so it survives the
    no-account exclusion filter.
    """
    from api.app import create_app
    from api.dependencies import get_service
    from fastapi.testclient import TestClient

    prob = Problem(
        id="prob-nocode",
        title="No Code Problem",
        slug="no-code-problem",
        difficulty=DifficultyLevel.EASY,
        platform="LeetCode",
        topics=["Array"],
    )
    attempt = Attempt(
        problem_id="prob-nocode",
        attempt_number=1,
        status=SubmissionStatus.WRONG_ANSWER,
        submissions=[
            Submission(
                problem_id="prob-nocode",
                code="",
                language="python",
                status=SubmissionStatus.WRONG_ANSWER,
                submitted_at=datetime.now(timezone.utc),
            )
        ],
    )
    prob.attempts.append(attempt)
    empty_service.storage.save(prob)

    app = create_app(service=empty_service)
    app.dependency_overrides[get_service] = lambda: empty_service

    with TestClient(app) as c:
        resp = c.get("/api/v1/submissions")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["code"] is None or items[0]["code"] == ""
        assert items[0]["status"] == "Wrong Answer"


def test_submission_detail_missing_runtime_memory(empty_service):
    """Submissions without runtime/memory must serialize as null.

    Uses source_provider=None so the submission survives without an active account.
    """
    from api.app import create_app
    from api.dependencies import get_service
    from fastapi.testclient import TestClient

    prob = Problem(
        id="prob-noruntime",
        title="No Runtime Problem",
        slug="no-runtime-problem",
        difficulty=DifficultyLevel.MEDIUM,
        platform="LeetCode",
        topics=["String"],
    )
    attempt = Attempt(
        problem_id="prob-noruntime",
        attempt_number=1,
        status=SubmissionStatus.COMPILE_ERROR,
        submissions=[
            Submission(
                problem_id="prob-noruntime",
                code="",
                language="java",
                status=SubmissionStatus.COMPILE_ERROR,
                submitted_at=datetime.now(timezone.utc),
            )
        ],
    )
    prob.attempts.append(attempt)
    empty_service.storage.save(prob)

    app = create_app(service=empty_service)
    app.dependency_overrides[get_service] = lambda: empty_service

    with TestClient(app) as c:
        resp = c.get("/api/v1/submissions")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["runtimeMs"] is None
        assert items[0]["memoryMb"] is None
        assert items[0]["status"] == "Compile Error"


def test_submission_list_deterministic_ordering(empty_service):
    """Submissions must be ordered newest → oldest, deterministically."""
    from api.app import create_app
    from api.dependencies import get_service
    from fastapi.testclient import TestClient

    base = datetime.now(timezone.utc)
    prob = Problem(
        id="prob-order",
        title="Ordering Problem",
        slug="ordering-problem",
        difficulty=DifficultyLevel.HARD,
        platform="LeetCode",
        topics=["DP"],
    )
    attempt = Attempt(
        problem_id="prob-order",
        attempt_number=1,
        status=SubmissionStatus.ACCEPTED,
        submissions=[
            Submission(
                problem_id="prob-order",
                code="x",
                language="python",
                status=SubmissionStatus.WRONG_ANSWER,
                submitted_at=base,
            ),
            Submission(
                problem_id="prob-order",
                code="y",
                language="python",
                status=SubmissionStatus.ACCEPTED,
                submitted_at=base.replace(hour=base.hour + 1, minute=0),
            ),
            Submission(
                problem_id="prob-order",
                code="z",
                language="python",
                status=SubmissionStatus.WRONG_ANSWER,
                submitted_at=base.replace(hour=base.hour + 2, minute=0),
            ),
        ],
    )
    prob.attempts.append(attempt)
    empty_service.storage.save(prob)

    app = create_app(service=empty_service)
    app.dependency_overrides[get_service] = lambda: empty_service

    with TestClient(app) as c:
        resp = c.get("/api/v1/submissions")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 3
        times = [datetime.fromisoformat(i["submittedAt"].replace("Z", "+00:00")) for i in items]
        assert times == sorted(times, reverse=True)


def test_submission_detail_includes_source_account(multi_account_service):
    """The API must expose source_account and source_provider.

    Uses the multi-account fixture: B (maytrix) is active and has a submission
    with source_provider set by the sync.
    """
    from api.app import create_app
    from api.dependencies import get_service
    from fastapi.testclient import TestClient

    app = create_app(service=multi_account_service)
    app.dependency_overrides[get_service] = lambda: multi_account_service

    with TestClient(app) as mc:
        resp = mc.get("/api/v1/submissions")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        data = items[0]
        assert data["sourceAccount"] == "maytrix"
        assert data["sourceProvider"] is not None


def _seed_submission_summary_population(service):
    """Create 123 rows so page sizes and aggregate values are distinguishable."""
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for problem_index in range(3):
        problem_id = f"summary-problem-{problem_index}"
        submissions = []
        for index in range(problem_index, 123, 3):
            status = (
                SubmissionStatus.ACCEPTED
                if index < 73
                else SubmissionStatus.WRONG_ANSWER
            )
            submissions.append(
                Submission(
                    id=f"summary-submission-{index}",
                    problem_id=problem_id,
                    attempt_id=f"summary-attempt-{problem_index}",
                    code="solution",
                    language="python" if index % 2 == 0 else "java",
                    status=status,
                    submitted_at=base + timedelta(seconds=index),
                    source_provider=None,
                    source_account=None,
                )
            )
        attempt = Attempt(
            id=f"summary-attempt-{problem_index}",
            problem_id=problem_id,
            attempt_number=1,
            status=SubmissionStatus.ACCEPTED,
            submissions=submissions,
        )
        service.storage.save(
            Problem(
                id=problem_id,
                title=f"Summary Problem {problem_index}",
                slug=f"summary-problem-{problem_index}",
                difficulty=DifficultyLevel.EASY,
                platform="LeetCode",
                attempts=[attempt],
            )
        )


@pytest.mark.parametrize("page_size", [20, 50, 100])
def test_submission_summary_is_independent_of_page_size(
    empty_service, page_size
):
    from api.app import create_app
    from api.dependencies import get_service
    from fastapi.testclient import TestClient

    _seed_submission_summary_population(empty_service)
    app = create_app(service=empty_service)
    app.dependency_overrides[get_service] = lambda: empty_service

    with TestClient(app) as test_client:
        response = test_client.get(f"/api/v1/submissions?page_size={page_size}")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == page_size
    assert data["total"] == 123
    assert data["summary"] == {
        "total": 123,
        "accepted": 73,
        "failed": 50,
        "acceptanceRate": pytest.approx(73 / 123 * 100),
        "problemCount": 3,
        "languageCount": 2,
    }
    assert data["summary"]["accepted"] + data["summary"]["failed"] == data["total"]


def test_submission_summary_is_independent_of_page_number(empty_service):
    from api.app import create_app
    from api.dependencies import get_service
    from fastapi.testclient import TestClient

    _seed_submission_summary_population(empty_service)
    app = create_app(service=empty_service)
    app.dependency_overrides[get_service] = lambda: empty_service

    with TestClient(app) as test_client:
        first = test_client.get("/api/v1/submissions?page=1&page_size=50").json()
        second = test_client.get("/api/v1/submissions?page=2&page_size=50").json()

    assert len(first["items"]) == len(second["items"]) == 50
    assert first["items"] != second["items"]
    assert first["summary"] == second["summary"]


@pytest.mark.parametrize(
    ("filters", "expected_total", "expected_accepted", "expected_failed"),
    [
        ({"status": "Accepted"}, 73, 73, 0),
        ({"language": "python"}, 62, 37, 25),
        ({"problem": "summary-problem-0"}, 41, 25, 16),
        (
            {"status": "Accepted", "language": "python", "problem": "summary-problem-0"},
            13,
            13,
            0,
        ),
    ],
)
def test_submission_filters_update_aggregate_summary(
    empty_service, filters, expected_total, expected_accepted, expected_failed
):
    from api.app import create_app
    from api.dependencies import get_service
    from fastapi.testclient import TestClient

    _seed_submission_summary_population(empty_service)
    app = create_app(service=empty_service)
    app.dependency_overrides[get_service] = lambda: empty_service

    with TestClient(app) as test_client:
        response = test_client.get("/api/v1/submissions", params=filters)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == expected_total
    assert data["summary"]["total"] == expected_total
    assert data["summary"]["accepted"] == expected_accepted
    assert data["summary"]["failed"] == expected_failed
    assert data["summary"]["acceptanceRate"] == pytest.approx(
        expected_accepted / expected_total * 100 if expected_total else 0
    )
