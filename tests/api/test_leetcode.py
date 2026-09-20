"""API-level regression tests for the LeetCode routes.

These drive the FastAPI app end to end through ``TestClient`` with the LeetCode
transport stubbed, so no request ever reaches leetcode.com. They cover the
behaviour the transport layer cannot see: that the engine's sync result is
projected into the API response shape, and that a genuine backend defect is
logged server-side instead of vanishing into a bare 500.
"""

import logging
import types
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from api.dependencies import get_service
from codememory.connectors.account.service import AccountService
from codememory.connectors.leetcode.models import LeetCodeSubmissionRaw
from codememory.connectors.leetcode.service import LeetCodeAccountService
from codememory.core.service import CodeMemoryService

_PROFILE = {
    "username": "syncuser",
    "real_name": "Sync User",
    "user_avatar": "https://leetcode.com/a.png",
    "ranking": 1234,
    "solved_all": 3,
    "solved_easy": 1,
    "solved_medium": 1,
    "solved_hard": 1,
}


def _raw(submission_id: str, title: str, slug: str) -> LeetCodeSubmissionRaw:
    """A raw accepted submission, exactly as the public API shapes it."""
    return LeetCodeSubmissionRaw(
        id=submission_id,
        submission_id=submission_id,
        title=title,
        title_slug=slug,
        language="python3",
        status="Accepted",
        timestamp=1700000000,
    )


def _mock_client() -> MagicMock:
    """A transport stub: two accepted submissions, no problem metadata fetch."""
    client = MagicMock()
    client.fetch_user_profile.return_value = _PROFILE
    client.fetch_user_submissions.return_value = [
        _raw("111", "Two Sum", "two-sum"),
        _raw("112", "Add Two Numbers", "add-two-numbers"),
    ]
    # No remote problem metadata: the engine falls back to what the submission
    # itself carries, which is enough to persist a problem locally.
    client.fetch_problem_details.return_value = None
    return client


@pytest.fixture
def connected_service(tmp_path: Path) -> CodeMemoryService:
    """A service with a validated LeetCode connection and a stubbed transport."""
    service = CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "leetcode_api.duckdb",
    )
    account_service = AccountService(data_dir=tmp_path / "data" / "accounts")
    leetcode = LeetCodeAccountService(
        service, account_service=account_service, client=_mock_client()
    )
    leetcode.connect("syncuser")
    # Install it so the lazy ``service.leetcode`` property returns this instance
    # rather than building one with a real client.
    service._leetcode_service = leetcode
    yield service
    service.close_storage()


@pytest.fixture
def client(connected_service: CodeMemoryService) -> TestClient:
    # Inject into the lifespan as well as the dependency override, so the server
    # never opens the real dev database (another server process may hold it).
    app = create_app(service=connected_service)
    app.dependency_overrides[get_service] = lambda: connected_service
    with TestClient(app) as client:
        yield client


def test_status_reports_connected_account(client: TestClient):
    response = client.get("/api/v1/leetcode/status")
    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is True
    assert data["username"] == "syncuser"


def test_sync_reports_imported_records(client: TestClient):
    """The API's ``recordsImported`` mirrors the engine's ``records_added``.

    Regression: the route read ``result.records_imported``, an attribute that
    does not exist on the domain ``SyncStatus`` (which names it
    ``records_added``). The resulting ``AttributeError`` was raised inside the
    route's own try block and swallowed by its catch-all handler, so every sync
    that actually reached this code returned a traceback-free HTTP 500.
    """
    response = client.post("/api/v1/leetcode/sync")

    assert response.status_code == 200, response.text
    data = response.json()

    assert data["status"] == "Success"
    assert data["recordsDiscovered"] == 2
    # Both submissions were new, so both were imported — not 0, and not a 500.
    assert data["recordsImported"] == 2
    assert data["recordsSkipped"] == 0
    assert data["recordsFailed"] == 0
    assert data["errorMessage"] is None


def test_sync_is_idempotent(client: TestClient):
    """A second sync over the same window imports nothing the second time."""
    first = client.post("/api/v1/leetcode/sync")
    assert first.status_code == 200
    assert first.json()["recordsImported"] == 2

    second = client.post("/api/v1/leetcode/sync")
    assert second.status_code == 200
    assert second.json()["recordsImported"] == 0
    assert second.json()["recordsSkipped"] == 2


def test_sync_reports_unexpected_failure_without_leaking_secrets(
    connected_service: CodeMemoryService,
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A real backend defect is logged with its traceback and reported safely.

    A LeetCode transport failure is absorbed by the engine into a FAILED
    ``SyncStatus``; only an unexpected exception reaches the route's catch-all.
    That case must not silently discard the cause.
    """
    # The deliberately fake secret proves the scrubber runs before the message
    # is handed back to a caller; no real credential is involved.
    failure_message = "storage write failed; password=[REDACTED]"

    def raising_sync(self: LeetCodeAccountService, limit: Any = None) -> Any:
        raise RuntimeError(failure_message)

    connected_service.leetcode.sync = types.MethodType(  # type: ignore[attr-defined]
        raising_sync, connected_service.leetcode
    )

    with caplog.at_level(logging.ERROR, logger="api.routes.leetcode"):
        response = client.post("/api/v1/leetcode/sync")

    assert response.status_code == 500, response.text

    # The caller learns the defect happened, but not the credential.
    assert "password" in response.text
    assert "fake-leak-token-123" not in response.text

    # The operator gets the traceback the previous handler threw away.
    assert any(
        record.name == "api.routes.leetcode"
        and record.levelno == logging.ERROR
        and "LeetCode sync failed" in record.getMessage()
        for record in caplog.records
    )
