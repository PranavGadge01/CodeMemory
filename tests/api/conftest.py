import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta

from codememory.core.service import CodeMemoryService
from codememory.domain.models import Problem, Submission, Attempt
from codememory.domain.enums import DifficultyLevel, SubmissionStatus

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
