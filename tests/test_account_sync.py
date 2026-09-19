"""Tests for LeetCode Account Connection & Sync Engine (Phase 8)."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from codememory.connectors.account.models import AccountConnection, AccountStatus, SyncState, SyncStatus
from codememory.connectors.account.service import AccountService
from codememory.connectors.leetcode.capabilities import LEETCODE_CAPABILITIES
from codememory.connectors.leetcode.mapper import LeetCodeMapper
from codememory.connectors.leetcode.models import LeetCodeProblemRaw, LeetCodeSubmissionRaw
from codememory.connectors.leetcode.sync import LeetCodeSyncEngine
from codememory.domain.exceptions import ProblemNotFoundError


# ──────────────────────────────────────────
# AccountService Tests
# ──────────────────────────────────────────


def test_account_service_save_and_get():
    """Test saving and retrieving an account connection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        svc = AccountService(data_dir=tmpdir)
        conn = AccountConnection(
            provider="LeetCode",
            username="testuser",
            display_name="Test User",
            status=AccountStatus.CONNECTED,
        )
        saved = svc.save_connection(conn)
        assert saved.username == "testuser"

        retrieved = svc.get_connection("LeetCode")
        assert retrieved is not None
        assert retrieved.username == "testuser"
        assert retrieved.status == AccountStatus.CONNECTED


def test_account_service_remove():
    """Test removing an account connection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        svc = AccountService(data_dir=tmpdir)
        conn = AccountConnection(provider="LeetCode", username="toremove")
        svc.save_connection(conn)
        assert svc.is_connected("LeetCode") is True

        result = svc.remove_connection("LeetCode")
        assert result is True
        assert svc.is_connected("LeetCode") is False


def test_account_service_not_connected():
    """Test querying non-existent connection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        svc = AccountService(data_dir=tmpdir)
        assert svc.get_connection("LeetCode") is None
        assert svc.is_connected("LeetCode") is False


# ──────────────────────────────────────────
# LeetCodeMapper.to_normalized_problem Tests
# ──────────────────────────────────────────


def test_mapper_to_normalized_problem():
    """Test converting LeetCodeProblemRaw to problem dict."""
    raw = LeetCodeProblemRaw(
        id="1",
        question_id="1",
        title="Two Sum",
        title_slug="two-sum",
        difficulty="Easy",
        topics=["Array", "Hash Table"],
        url="https://leetcode.com/problems/two-sum/",
        content="<p>Given an array...</p>",
    )
    result = LeetCodeMapper.to_normalized_problem(raw)
    assert result["title"] == "Two Sum"
    assert result["slug"] == "two-sum"
    assert result["difficulty"] == "Easy"
    assert result["topics"] == ["Array", "Hash Table"]
    assert "leetcode.com" in result["url"]
    assert result["statement"] == "<p>Given an array...</p>"


def test_mapper_to_normalized_problem_defaults():
    """Test defaults when optional fields are missing."""
    raw = LeetCodeProblemRaw(
        title="Merge Intervals",
        title_slug="merge-intervals",
    )
    result = LeetCodeMapper.to_normalized_problem(raw)
    assert result["title"] == "Merge Intervals"
    assert result["slug"] == "merge-intervals"
    assert result["topics"] == []
    assert result["statement"] is None


# ──────────────────────────────────────────
# LeetCodeSyncEngine Tests
# ──────────────────────────────────────────


def test_sync_engine_connect_account():
    """Test connect_account validates profile and persists connection."""
    mock_client = MagicMock()
    mock_client.fetch_user_profile.return_value = {
        "username": "neal_wu",
        "real_name": "Neal Wu",
        "user_avatar": "https://example.com/avatar.png",
        "ranking": 42,
        "solved_all": 500,
        "solved_easy": 200,
        "solved_medium": 200,
        "solved_hard": 100,
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        acct_svc = AccountService(data_dir=tmpdir)
        engine = LeetCodeSyncEngine(account_service=acct_svc, client=mock_client)
        conn = engine.connect_account("neal_wu")

        assert conn.username == "neal_wu"
        assert conn.display_name == "Neal Wu"
        assert conn.status == AccountStatus.CONNECTED
        assert conn.metadata["solved_all"] == 500

        # Verify persisted
        retrieved = acct_svc.get_connection("LeetCode")
        assert retrieved is not None
        assert retrieved.username == "neal_wu"


def test_sync_engine_connect_invalid_username():
    """Test connect_account raises on empty username."""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = LeetCodeSyncEngine(account_service=AccountService(data_dir=tmpdir))
        with pytest.raises(ValueError, match="empty"):
            engine.connect_account("")


def test_sync_engine_connect_profile_not_found():
    """Test connect_account raises when profile cannot be fetched."""
    mock_client = MagicMock()
    mock_client.fetch_user_profile.return_value = None

    with tempfile.TemporaryDirectory() as tmpdir:
        engine = LeetCodeSyncEngine(
            account_service=AccountService(data_dir=tmpdir),
            client=mock_client,
        )
        with pytest.raises(ValueError, match="could not be validated"):
            engine.connect_account("nonexistent_user_xyz")


def test_sync_engine_sync_not_connected():
    """Test sync raises when no account is connected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = LeetCodeSyncEngine(account_service=AccountService(data_dir=tmpdir))
        with pytest.raises(ValueError, match="not connected"):
            engine.sync(MagicMock())


def test_sync_engine_disconnect():
    """Test disconnect removes connection metadata."""
    mock_client = MagicMock()
    mock_client.fetch_user_profile.return_value = {
        "username": "test_user",
        "real_name": "Test",
        "solved_all": 10,
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        acct_svc = AccountService(data_dir=tmpdir)
        engine = LeetCodeSyncEngine(account_service=acct_svc, client=mock_client)
        engine.connect_account("test_user")
        assert acct_svc.is_connected("LeetCode") is True

        result = engine.disconnect_account()
        assert result is True
        assert acct_svc.is_connected("LeetCode") is False


def test_sync_engine_full_sync_flow():
    """Test full sync flow: profile update, submission fetch, add to service."""
    mock_client = MagicMock()
    mock_client.fetch_user_profile.return_value = {
        "username": "sync_user",
        "real_name": "Sync User",
        "user_avatar": None,
        "ranking": 100,
        "solved_all": 50,
        "solved_easy": 20,
        "solved_medium": 20,
        "solved_hard": 10,
    }
    mock_client.fetch_user_submissions.return_value = [
        LeetCodeSubmissionRaw(
            id="111",
            submission_id="111",
            title="Two Sum",
            title_slug="two-sum",
            language="python3",
            status="Accepted",
            timestamp=1700000000,
        ),
    ]

    # Mock service that has no existing problem
    mock_service = MagicMock()
    mock_service.get_problem.side_effect = ProblemNotFoundError("two-sum")

    mock_client.fetch_problem_details.return_value = LeetCodeProblemRaw(
        id="1",
        question_id="1",
        title="Two Sum",
        title_slug="two-sum",
        difficulty="Easy",
        topics=["Array", "Hash Table"],
        url="https://leetcode.com/problems/two-sum/",
    )

    mock_problem = MagicMock()
    mock_problem.slug = "two-sum"
    mock_problem.attempts = []
    mock_service.add_problem.return_value = mock_problem

    # add_submission() returns (problem, submission) in production; the stored
    # submission carries the external LeetCode id.
    mock_stored = MagicMock()
    mock_stored.id = "leetcode_111"
    mock_service.add_submission.return_value = (mock_problem, mock_stored)

    with tempfile.TemporaryDirectory() as tmpdir:
        acct_svc = AccountService(data_dir=tmpdir)
        engine = LeetCodeSyncEngine(account_service=acct_svc, client=mock_client)

        # Pre-connect
        conn = AccountConnection(
            provider="LeetCode",
            username="sync_user",
            status=AccountStatus.CONNECTED,
        )
        acct_svc.save_connection(conn)

        result = engine.sync(mock_service)

        assert result.status == SyncState.SUCCESS
        assert result.records_discovered == 1
        assert result.records_added == 1
        assert result.records_skipped == 0
        mock_service.add_problem.assert_called_once()
        mock_service.add_submission.assert_called_once()


# ──────────────────────────────────────────
# Capability Constants Tests
# ──────────────────────────────────────────


def test_capabilities_structure():
    """Verify capability constants match expected shape."""
    assert LEETCODE_CAPABILITIES["profile_sync"] is True
    assert LEETCODE_CAPABILITIES["progress_sync"] is True
    assert LEETCODE_CAPABILITIES["recent_submissions"] is True
    assert LEETCODE_CAPABILITIES["private_code_scraping"] is False
