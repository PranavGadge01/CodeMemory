import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock

from codememory.core.service import CodeMemoryService
from codememory.domain.models import Problem, Submission, Attempt
from codememory.domain.enums import DifficultyLevel, SubmissionStatus
from codememory.connectors.account.service import AccountService
from codememory.connectors.leetcode.models import LeetCodeSubmissionRaw
from codememory.connectors.leetcode.service import LeetCodeAccountService

from api.app import create_app
from api.dependencies import get_service

@pytest.fixture
def mock_service():
    """Provides a real CodeMemoryService backed by an in-memory database."""
    service = CodeMemoryService(db_path=":memory:")
    
    # Seed some mock data so the DB isn't completely empty
    prob = Problem(
        id="mock-1",
        title="Two Sum",
        slug="two-sum",
        difficulty=DifficultyLevel.EASY,
        platform="LeetCode",
        topics=["Array", "Hash Table"]
    )
    
    attempt = Attempt(
        problem_id="mock-1",
        attempt_number=1,
        status=SubmissionStatus.ACCEPTED,
        submissions=[
            Submission(
                problem_id="mock-1",
                code="print('hello')",
                language="python",
                status=SubmissionStatus.ACCEPTED,
                submitted_at=datetime.now(timezone.utc)
            )
        ]
    )
    prob.attempts.append(attempt)
    
    # Bypass the service layer's import mechanisms for the test seed to just write it
    service.storage.save(prob)
    
    yield service
    
    service.close_storage()


@pytest.fixture
def empty_service():
    """Provides a CodeMemoryService with no data."""
    service = CodeMemoryService(db_path=":memory:")
    yield service
    service.close_storage()


@pytest.fixture
def streak_service():
    """Provides a service with controlled submission dates for streak testing.
    
    Creates submissions on:
    - Today (1 submission accepted)
    - Yesterday (1 submission accepted)  
    - 2 days ago (1 submission accepted)
    - 5 days ago (1 submission - creates a gap)
    Also creates multiple submissions on today for same-day dedup testing.
    """
    service = CodeMemoryService(db_path=":memory:")
    today = datetime.now(timezone.utc).replace(hour=10, minute=0, second=0, microsecond=0)
    
    # Problem 1: submissions today (multiple submissions same day -> 1 active day)
    prob1 = Problem(
        id="prob-streak-1",
        title="Streak Problem 1",
        slug="streak-problem-1",
        difficulty=DifficultyLevel.EASY,
        platform="LeetCode",
        topics=["Array"]
    )
    attempt1 = Attempt(
        problem_id="prob-streak-1",
        attempt_number=1,
        status=SubmissionStatus.ACCEPTED,
        submissions=[
            Submission(
                problem_id="prob-streak-1",
                code="solution",
                language="python",
                status=SubmissionStatus.ACCEPTED,
                submitted_at=today,
            ),
            Submission(
                problem_id="prob-streak-1",
                code="wrong",
                language="python",
                status=SubmissionStatus.WRONG_ANSWER,
                submitted_at=today + timedelta(hours=2),
            ),
        ]
    )
    prob1.attempts.append(attempt1)
    service.storage.save(prob1)
    
    # Problem 2: submission yesterday
    prob2 = Problem(
        id="prob-streak-2",
        title="Streak Problem 2",
        slug="streak-problem-2",
        difficulty=DifficultyLevel.MEDIUM,
        platform="LeetCode",
        topics=["Hash Table"]
    )
    attempt2 = Attempt(
        problem_id="prob-streak-2",
        attempt_number=1,
        status=SubmissionStatus.ACCEPTED,
        submissions=[
            Submission(
                problem_id="prob-streak-2",
                code="solution",
                language="cpp",
                status=SubmissionStatus.ACCEPTED,
                submitted_at=today - timedelta(days=1),
            )
        ]
    )
    prob2.attempts.append(attempt2)
    service.storage.save(prob2)
    
    # Problem 3: submission 2 days ago
    prob3 = Problem(
        id="prob-streak-3",
        title="Streak Problem 3",
        slug="streak-problem-3",
        difficulty=DifficultyLevel.HARD,
        platform="LeetCode",
        topics=["Dynamic Programming"]
    )
    attempt3 = Attempt(
        problem_id="prob-streak-3",
        attempt_number=1,
        status=SubmissionStatus.WRONG_ANSWER,
        submissions=[
            Submission(
                problem_id="prob-streak-3",
                code="failed",
                language="python",
                status=SubmissionStatus.WRONG_ANSWER,
                submitted_at=today - timedelta(days=2),
            )
        ]
    )
    prob3.attempts.append(attempt3)
    service.storage.save(prob3)
    
    # Problem 4: submission 5 days ago (creates gap between day 4 and day 2)
    prob4 = Problem(
        id="prob-streak-4",
        title="Streak Problem 4",
        slug="streak-problem-4",
        difficulty=DifficultyLevel.EASY,
        platform="LeetCode",
        topics=["String"]
    )
    attempt4 = Attempt(
        problem_id="prob-streak-4",
        attempt_number=1,
        status=SubmissionStatus.ACCEPTED,
        submissions=[
            Submission(
                problem_id="prob-streak-4",
                code="solution",
                language="java",
                status=SubmissionStatus.ACCEPTED,
                submitted_at=today - timedelta(days=5),
            )
        ]
    )
    prob4.attempts.append(attempt4)
    service.storage.save(prob4)
    
    yield service
    service.close_storage()


@pytest.fixture
def client(mock_service):
    """Provides a TestClient with the mocked service dependency overridden."""
    # Inject the isolated service into the lifespan too: the server otherwise
    # builds its own against the real dev database, which a concurrent server
    # process may already hold locked. The dependency override alone only covers
    # request resolution, not app startup.
    app = create_app(service=mock_service)

    # Override the dependency to use our isolated fixture service
    app.dependency_overrides[get_service] = lambda: mock_service

    with TestClient(app) as client:
        yield client


@pytest.fixture
def empty_client(empty_service):
    """Provides a TestClient with an empty service for edge-case testing."""
    app = create_app(service=empty_service)
    app.dependency_overrides[get_service] = lambda: empty_service
    with TestClient(app) as client:
        yield client


@pytest.fixture
def streak_client(streak_service):
    """Provides a TestClient with the streak test data."""
    app = create_app(service=streak_service)
    app.dependency_overrides[get_service] = lambda: streak_service
    with TestClient(app) as client:
        yield client


def _raw(submission_id: str, title: str, slug: str, timestamp: int,
         status: str = "Accepted", language: str = "python3"):
    return LeetCodeSubmissionRaw(
        id=submission_id, submission_id=submission_id,
        title=title, title_slug=slug, language=language,
        status=status, timestamp=timestamp,
    )


def _mock_client(submissions, username: str):
    client = MagicMock()
    client.fetch_user_profile.return_value = {
        "username": username,
        "real_name": username,
        "user_avatar": None,
        "ranking": 9999,
        "solved_all": 1,
        "solved_easy": 1,
        "solved_medium": 0,
        "solved_hard": 0,
    }
    client.fetch_user_submissions.return_value = submissions
    client.fetch_problem_details.return_value = None
    return client


def _make_multi_account_service(tmp_path: Path):
    """Build a service with two LeetCode accounts (A: jaypatil1229, B: maytrix).

    Account A has 2 accepted submissions; account B has 1 accepted submission.
    Both are synced into the shared DuckDB via separate connect+sync cycles.
    The service is left with account B as the active connection.
    """
    import time
    now_ts = int(time.time())

    account_service = AccountService(data_dir=tmp_path / "accounts")
    service = CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "multi_account.duckdb",
        account_service=account_service,
    )

    # Account A: jaypatil1229 — two submissions (both accepted, same problem)
    surface = LeetCodeAccountService(
        app_service=service,
        account_service=account_service,
        client=_mock_client([
            _raw("1001", "Two Sum", "two-sum", now_ts),
            _raw("1002", "Two Sum", "two-sum", now_ts - 86400, status="Accepted", language="python3"),
        ], "jaypatil1229"),
    )
    surface.connect("jaypatil1229")
    surface.sync()

    # Account B: maytrix — one submission (accepted, different problem)
    surface_b = LeetCodeAccountService(
        app_service=service,
        account_service=account_service,
        client=_mock_client([
            _raw("2001", "Add Two Numbers", "add-two-numbers", now_ts - 172800),
        ], "maytrix"),
    )
    surface_b.connect("maytrix")
    surface_b.sync()

    # Install the surface so service.leetcode returns the last one connected
    service._leetcode_service = surface_b
    return service


@pytest.fixture
def multi_account_service(tmp_path: Path):
    service = _make_multi_account_service(tmp_path)
    yield service
    service.close_storage()


@pytest.fixture
def multi_account_client(multi_account_service):
    app = create_app(service=multi_account_service)
    app.dependency_overrides[get_service] = lambda: multi_account_service
    with TestClient(app) as client:
        yield client


@pytest.fixture
def multi_account_service_factory(tmp_path: Path):
    """Factory that returns a fresh multi-account service for each call."""
    yield lambda: _make_multi_account_service(tmp_path)
