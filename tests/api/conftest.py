import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone

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
