"""Phase C — account/sync service-surface tests.

These exercise the service layer only: ``CodeMemoryService.leetcode`` and
:class:`LeetCodeAccountService`. A consumer of this surface never constructs or
calls the low-level LeetCode client, and every test is fully mocked — none of
them reaches the network.

The Phase B engine contract underneath is assumed verified by
``test_leetcode_sync_phase_b.py``; what is verified here is that the surface
preserves it and projects it honestly.
"""

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from codememory.connectors.account.models import AccountStatus, SyncState
from codememory.connectors.account.service import AccountService
from codememory.connectors.leetcode import service as service_module
from codememory.connectors.leetcode.errors import LeetCodePermanentError
from codememory.connectors.leetcode.models import LeetCodeSubmissionRaw
from codememory.connectors.leetcode.service import (
    LeetCodeAccountError,
    LeetCodeAccountService,
    safe_error_message,
)
from codememory.connectors.leetcode.sync import UNAVAILABLE_FIELDS
from codememory.core.service import CodeMemoryService

_PROFILE_SENTINEL = object()

_PROFILE = {
    "username": "syncuser",
    "real_name": "Sync User",
    "user_avatar": "https://leetcode.com/a.png",
    "ranking": 1234,
    "solved_all": 42,
    "solved_easy": 20,
    "solved_medium": 15,
    "solved_hard": 7,
}


def _raw(**overrides) -> LeetCodeSubmissionRaw:
    """A raw LeetCode accepted submission, exactly as the public API shapes it.

    No code, no runtime, no memory — the supported endpoint supplies none of
    them, and the service must not invent stand-ins.
    """
    base: dict[str, Any] = dict(
        id="111",
        submission_id="111",
        title="Two Sum",
        title_slug="two-sum",
        language="python3",
        status="Accepted",
        timestamp=1700000000,
    )
    base.update(overrides)
    # The real client populates both fields from the same value; keep them
    # aligned here so an override of ``id`` cannot quietly change dedup keys.
    if "submission_id" not in overrides:
        base["submission_id"] = str(base["id"])
    return LeetCodeSubmissionRaw(**base)


def _make_service(tmp_path: Path) -> CodeMemoryService:
    return CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "phase_c.duckdb",
    )


def _mock_client(submissions=None, *, profile=_PROFILE_SENTINEL) -> MagicMock:
    client = MagicMock()
    client.fetch_user_profile.return_value = _PROFILE if profile is _PROFILE_SENTINEL else profile
    client.fetch_user_submissions.return_value = (
        [_raw()] if submissions is None else submissions
    )
    # No problem metadata: the fallback path creates the problem from the
    # submission record, which keeps these tests off the network entirely.
    client.fetch_problem_details.return_value = None
    return client


def _surface(
    tmp_path: Path, client: MagicMock | None = None
) -> tuple[LeetCodeAccountService, CodeMemoryService]:
    service = _make_service(tmp_path)
    surface = LeetCodeAccountService(
        app_service=service,
        account_service=AccountService(data_dir=tmp_path / "accounts"),
        client=client or _mock_client(),
    )
    return surface, service


def _stored_submissions(service: CodeMemoryService) -> list:
    return [s for p in service.list_problems() for a in p.attempts for s in a.submissions]


def _account_file(tmp_path: Path) -> dict:
    raw = (tmp_path / "accounts" / "account_connections.json").read_text()
    return json.loads(raw)


# ─────────────────────────────────────────────────────────────────────────────
# 1. CONNECT
# ─────────────────────────────────────────────────────────────────────────────


def test_status_before_connect(tmp_path):
    """An untouched account reports NOT_CONNECTED with nothing implied."""
    surface, _ = _surface(tmp_path)

    status = surface.status()

    assert status.connected is False
    assert status.account_status == AccountStatus.NOT_CONNECTED
    assert status.sync_state == SyncState.IDLE
    assert status.username is None
    assert status.last_attempted_sync is None
    assert status.last_successful_sync is None
    assert status.records_imported is None
    assert status.coverage is None
    assert status.last_error is None


def test_connect_validates_and_persists_identity(tmp_path):
    """A valid public profile becomes a connected account with minimal metadata."""
    client = _mock_client()
    surface, service = _surface(tmp_path, client)

    conn = surface.connect("syncuser")

    assert surface.is_connected() is True
    assert conn.username == "syncuser"
    assert conn.display_name == "Sync User"
    assert conn.status == AccountStatus.CONNECTED
    assert conn.metadata["solved_all"] == 42

    client.fetch_user_profile.assert_called_once_with("syncuser")

    status = surface.status()
    assert status.connected is True
    assert status.username == "syncuser"
    assert status.sync_state == SyncState.IDLE, "no sync has run yet"


def test_connect_failed_validation_leaves_no_connection(tmp_path):
    """A profile the API does not confirm must never look connected."""
    client = _mock_client(profile=None)
    surface, service = _surface(tmp_path, client)

    with pytest.raises(ValueError, match="could not be validated"):
        surface.connect("does_not_exist_xyz")

    assert surface.is_connected() is False
    assert surface.status().connected is False
    assert surface.status().account_status == AccountStatus.NOT_CONNECTED
    # Nothing was persisted at all.
    assert not (tmp_path / "accounts" / "account_connections.json").exists()


def test_connect_rejects_empty_username(tmp_path):
    surface, _ = _surface(tmp_path)

    with pytest.raises(ValueError, match="empty"):
        surface.connect("   ")

    assert surface.is_connected() is False


def test_reconnect_is_idempotent(tmp_path):
    """Connecting the connected account again is a no-op, not a second record."""
    client = _mock_client()
    surface, _ = _surface(tmp_path, client)

    first = surface.connect("syncuser")
    second = surface.connect("syncuser")

    assert first.username == second.username
    assert surface.is_connected() is True
    # One validation, one persisted record: a double click cannot duplicate state.
    client.fetch_user_profile.assert_called_once()
    assert set(_account_file(tmp_path)) == {"leetcode"}


def test_connect_transport_failure_is_safe_and_unpersisted(tmp_path):
    """A typed transport error is translated, scrubbed and leaves no connection."""
    client = _mock_client()
    client.fetch_user_profile.side_effect = LeetCodePermanentError(
        "rejected with HTTP 401 (cookie: LEETCODE_SESSION=FAKE_SESSION_VALUE_123)"
    )
    surface, _ = _surface(tmp_path, client)

    with pytest.raises(LeetCodeAccountError) as excinfo:
        surface.connect("syncuser")

    assert "FAKE_SESSION_VALUE_123" not in str(excinfo.value)
    assert surface.is_connected() is False


def test_no_credentials_are_persisted(tmp_path):
    """The connection store holds identity/profile data only."""
    surface, _ = _surface(tmp_path)
    surface.connect("syncuser")

    blob = json.dumps(_account_file(tmp_path)).lower()
    for secret in ("password", "cookie", "token", "session", "authorization", "bearer"):
        assert secret not in blob, f"credential-shaped key leaked into storage: {secret}"


# ─────────────────────────────────────────────────────────────────────────────
# 2. SYNC
# ─────────────────────────────────────────────────────────────────────────────


def test_initial_sync_through_service_layer(tmp_path):
    """The service surface drives the engine end to end."""
    client = _mock_client([_raw()])
    surface, service = _surface(tmp_path, client)
    surface.connect("syncuser")

    result = surface.sync()

    assert result.status == SyncState.SUCCESS
    assert result.records_added == 1
    assert result.records_discovered == 1
    assert len(_stored_submissions(service)) == 1
    # No low-level client was needed to reach this point — only the surface.
    assert client.fetch_user_submissions.call_count == 1


def test_repeated_sync_is_idempotent(tmp_path):
    """The same window synced twice yields one stored submission."""
    client = _mock_client([_raw()])
    surface, service = _surface(tmp_path, client)
    surface.connect("syncuser")

    first = surface.sync()
    second = surface.sync()

    assert first.records_added == 1
    assert second.records_added == 0
    assert second.records_skipped == 1
    assert len(_stored_submissions(service)) == 1


def test_partial_status_propagates(tmp_path):
    """A record that fails to persist makes the run PARTIAL, never SUCCESS."""
    client = _mock_client([_raw(id="111"), _raw(id="112", timestamp=1700003600)])
    surface, service = _surface(tmp_path, client)
    surface.connect("syncuser")
    original = service.add_submission

    def failing_add(*args, **kwargs):
        if kwargs.get("submission_id") == "leetcode_112":
            raise RuntimeError("storage is down")
        return original(*args, **kwargs)

    service.add_submission = failing_add
    result = surface.sync()

    assert result.status == SyncState.PARTIAL
    assert result.records_failed == 1
    assert result.records_added == 1

    status = surface.status()
    assert status.sync_state == SyncState.PARTIAL
    assert status.records_failed == 1
    assert status.records_imported == 1
    # PARTIAL is an attempt, not a success — nothing may claim otherwise.
    assert status.last_successful_sync is None
    assert status.last_attempted_sync is not None


def test_gap_and_coverage_propagate_to_status(tmp_path):
    """Coverage, window and gap signals reach the status object unchanged."""
    client = _mock_client(
        [
            _raw(id="111", timestamp=1700000000),
            _raw(id="112", timestamp=1700003600),
        ]
    )
    surface, _ = _surface(tmp_path, client)
    surface.connect("syncuser")

    first = surface.sync()
    assert first.details["gap_detected"] is False

    client.fetch_user_submissions.return_value = [
        _raw(id="121", timestamp=1700010000),
        _raw(id="122", timestamp=1700013600),
    ]
    second = surface.sync()

    assert second.details["gap_detected"] is True
    assert second.details["coverage"] == "recent-window"

    status = surface.status()
    assert status.coverage == "recent-window"
    assert status.gap_detected is True
    assert status.window_limit == 20
    assert status.records_in_window == 2
    assert status.window_truncated is False
    assert status.unavailable_fields == UNAVAILABLE_FIELDS


def test_status_after_successful_sync(tmp_path):
    """A clean sync is reported as the last success with honest counts."""
    client = _mock_client([_raw()])
    surface, service = _surface(tmp_path, client)

    surface.connect("syncuser")
    result = surface.sync()

    status = surface.status()
    assert status.connected is True
    assert status.sync_state == SyncState.SUCCESS
    assert status.records_imported == result.records_added == 1
    assert status.records_skipped == 0
    assert status.records_failed == 0
    assert status.last_attempted_sync is not None
    assert status.last_successful_sync is not None
    assert status.last_error is None


def test_status_survives_a_fresh_service_instance(tmp_path):
    """The last sync is projected onto persisted state, not in-process memory."""
    client = _mock_client([_raw()])
    surface, service = _surface(tmp_path, client)
    surface.connect("syncuser")
    surface.sync()

    # A surface built after the fact, sharing nothing but the account store.
    reopened = LeetCodeAccountService(
        app_service=service,
        account_service=AccountService(data_dir=tmp_path / "accounts"),
        client=client,
    )
    status = reopened.status()

    assert status.connected is True
    assert status.username == "syncuser"
    assert status.sync_state == SyncState.SUCCESS
    assert status.records_imported == 1
    assert status.coverage == "recent-window"


# ─────────────────────────────────────────────────────────────────────────────
# 3. DISCONNECT
# ─────────────────────────────────────────────────────────────────────────────


def test_disconnect_reports_not_connected(tmp_path):
    surface, _ = _surface(tmp_path)
    surface.connect("syncuser")
    assert surface.is_connected() is True

    assert surface.disconnect() is True

    status = surface.status()
    assert status.connected is False
    assert status.account_status == AccountStatus.NOT_CONNECTED
    assert status.username is None
    assert status.sync_state == SyncState.IDLE


def test_disconnect_preserves_imported_submissions(tmp_path):
    """Disconnecting removes connection state, never coding history."""
    client = _mock_client([_raw()])
    surface, service = _surface(tmp_path, client)
    surface.connect("syncuser")
    surface.sync()
    assert len(_stored_submissions(service)) == 1

    surface.disconnect()

    assert len(_stored_submissions(service)) == 1, "imported history must survive disconnect"
    assert list(service.list_problems())


def test_reconnect_after_disconnect_keeps_history(tmp_path):
    """A fresh connection starts from valid account state with no deletion."""
    client = _mock_client([_raw()])
    surface, service = _surface(tmp_path, client)
    surface.connect("syncuser")
    surface.sync()
    surface.disconnect()

    conn = surface.connect("syncuser")
    assert conn.status == AccountStatus.CONNECTED
    assert surface.is_connected() is True

    result = surface.sync()
    # The pre-disconnect submission is still there, so nothing is re-added.
    assert result.records_added == 0
    assert result.records_skipped == 1
    assert len(_stored_submissions(service)) == 1


def test_sync_without_connection_raises(tmp_path):
    """No silent success when nothing is connected."""
    surface, _ = _surface(tmp_path)

    with pytest.raises(ValueError, match="not connected"):
        surface.sync()


# ─────────────────────────────────────────────────────────────────────────────
# 4. Safe error handling
# ─────────────────────────────────────────────────────────────────────────────


_SECRET_MESSAGE = (
    "request failed for syncuser; Cookie: LEETCODE_SESSION=FAKE_SESSION_VALUE_123; "
    "Authorization: Bearer <AUTH_TOKEN>; body={\"query\": \"query recentAcSubmissions\"}"
)


def test_safe_error_message_destroys_secrets():
    cleaned = safe_error_message(_SECRET_MESSAGE)

    for secret in ("FAKE_SESSION_VALUE_123", "<AUTH_TOKEN>", "recentAcSubmissions"):
        assert secret not in cleaned
    assert "<redacted>" in cleaned
    assert "request failed" in cleaned, "the actionable part must survive scrubbing"


def test_safe_error_message_bounds_length():
    long = "boom " * 200
    cleaned = safe_error_message(long)
    assert len(cleaned) <= 400
    assert cleaned.endswith("...")


def test_safe_error_message_handles_nothing():
    assert safe_error_message(None) == ""
    assert safe_error_message("") == ""


def test_sync_error_is_scrubbed_before_it_reaches_callers(tmp_path):
    """A failure carrying secrets must not leak them through the result or status."""
    client = _mock_client()
    client.fetch_user_submissions.side_effect = RuntimeError(_SECRET_MESSAGE)
    surface, _ = _surface(tmp_path, client)
    surface.connect("syncuser")

    result = surface.sync()

    assert result.status == SyncState.FAILED
    for secret in ("FAKE_SESSION_VALUE_123", "<AUTH_TOKEN>", "recentAcSubmissions"):
        assert secret not in (result.error_message or "")

    status = surface.status()
    assert status.sync_state == SyncState.FAILED
    assert status.last_error is not None
    assert "FAKE_SESSION_VALUE_123" not in status.last_error
    assert status.last_successful_sync is None

    # Nor did the secret reach the persisted connection record.
    blob = json.dumps(_account_file(tmp_path))
    assert "FAKE_SESSION_VALUE_123" not in blob


# ─────────────────────────────────────────────────────────────────────────────
# 5. Consumer surface hygiene
# ─────────────────────────────────────────────────────────────────────────────


def test_consumer_needs_no_low_level_client(tmp_path):
    """The surface exposes the lifecycle and nothing of the transport."""
    surface, _ = _surface(tmp_path)

    public = {name for name in dir(surface) if not name.startswith("_")}
    assert {"connect", "sync", "status", "disconnect", "is_connected"} <= public
    assert not any(
        token in name.lower() for name in public for token in ("client", "engine", "transport")
    ), "the consumer surface must not expose the low-level client"

    # The surface module does not even name the transport client, so no consumer
    # path can reach it through this object.
    assert "LeetCodeClient" not in dir(service_module), "the transport client must not be reachable"


def test_code_memory_service_exposes_the_surface(tmp_path):
    """``CodeMemoryService.leetcode`` is the single service-level entry point."""
    service = _make_service(tmp_path)

    assert isinstance(service.leetcode, LeetCodeAccountService)
    assert service.leetcode is service.leetcode, "the surface is cached, not rebuilt per access"
    # The account store lives with the service's own data directory.
    assert service.leetcode.status().connected is False
