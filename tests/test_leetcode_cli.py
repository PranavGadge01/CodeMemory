"""Phase D — CLI integration tests for the LeetCode account/sync lifecycle.

The commands must talk to the canonical ``service.leetcode`` surface only, never
to the sync engine or the GraphQL client. Every test is fully mocked: no network,
no filesystem state outside ``tmp_path``.
"""

import inspect
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from codememory.cli.main import build_parser, main, render_leetcode_status
from codememory.connectors.account.models import SyncState, SyncStatus
from codememory.connectors.leetcode.service import LeetCodeAccountError, LeetCodeAccountStatus

# ``codememory.cli.main`` resolves to the *function* through the package export,
# so the module object is fetched explicitly for monkeypatching and inspection.
cli_main = sys.modules["codememory.cli.main"]

SECRET_COOKIE = "LEETCODE_SESSION=FAKE_SESSION_VALUE_123"


class FakeLeetCode:
    """Stand-in for the ``service.leetcode`` surface, recording every call."""

    def __init__(self) -> None:
        self.connect_calls: list[str] = []
        self.connect_error: Exception | None = None
        self.sync_calls: list = []
        self.sync_result: SyncStatus | None = None
        self.sync_error: Exception | None = None
        self.disconnect_error: Exception | None = None
        self.status_value = LeetCodeAccountStatus()
        self.disconnect_count = 0
        # Pretend history imported before the account was connected.
        self.history = ["two-sum", "3sum"]

    def is_connected(self) -> bool:
        return self.status_value.connected

    def connect(self, username: str):
        self.connect_calls.append(username)
        if self.connect_error is not None:
            raise self.connect_error
        self.status_value = LeetCodeAccountStatus(
            connected=True, username=username, display_name=username.title()
        )
        return SimpleNamespace(username=username, display_name=username.title())

    def sync(self, limit=None) -> SyncStatus:
        self.sync_calls.append(limit)
        if self.sync_error is not None:
            raise self.sync_error
        return self.sync_result  # type: ignore[return-value]

    def status(self) -> LeetCodeAccountStatus:
        return self.status_value

    def disconnect(self) -> bool:
        self.disconnect_count += 1
        if self.disconnect_error is not None:
            raise self.disconnect_error
        was_connected = self.status_value.connected
        self.status_value = LeetCodeAccountStatus()
        return was_connected


@pytest.fixture
def leetcode(monkeypatch) -> FakeLeetCode:
    """Replace the CLI's service with one whose LeetCode surface is a stub."""
    fake = FakeLeetCode()
    service = SimpleNamespace(leetcode=fake, history=fake.history)
    monkeypatch.setattr(cli_main, "CodeMemoryService", lambda *a, **k: service)
    return fake


def _output(capsys) -> str:
    return capsys.readouterr().out


def _sync(**overrides) -> SyncStatus:
    base = dict(
        status=SyncState.SUCCESS,
        records_discovered=3,
        records_added=3,
        records_skipped=0,
        records_failed=0,
        error_message=None,
        details={
            "coverage": "recent-window",
            "window_limit": 20,
            "records_in_window": 3,
            "window_truncated": False,
            "gap_detected": False,
            "unavailable_fields": ["code", "runtime_ms", "memory_mb"],
        },
    )
    base.update(overrides)
    return SyncStatus(**base)


# ─────────────────────────────────────────────────────────────────────────────
# Parser
# ─────────────────────────────────────────────────────────────────────────────


def test_parser_supports_account_actions():
    parser = build_parser()
    for action in ("connect", "sync", "status", "disconnect", "import", "preview", "validate"):
        parsed = parser.parse_args(["leetcode", action, "x"])
        assert parsed.action == action


def test_parser_makes_path_optional_for_account_actions():
    """``sync``/``status``/``disconnect`` take no file argument."""
    parser = build_parser()
    parsed = parser.parse_args(["leetcode", "status"])
    assert parsed.path is None


def test_parser_accepts_sync_limit():
    parser = build_parser()
    assert parser.parse_args(["leetcode", "sync", "--limit", "5"]).limit == 5


# ─────────────────────────────────────────────────────────────────────────────
# connect
# ─────────────────────────────────────────────────────────────────────────────


def test_cli_connect_success(capsys, leetcode):
    main(["leetcode", "connect", "neal_wu"])

    assert leetcode.connect_calls == ["neal_wu"]
    out = _output(capsys)
    assert "Connected to LeetCode account" in out
    assert "@neal_wu" in out
    assert "no password" in out.lower() or "no password" in out


def test_cli_connect_without_username_exits_nonzero(capsys, leetcode):
    with pytest.raises(SystemExit) as excinfo:
        main(["leetcode", "connect"])

    assert excinfo.value.code == 1
    assert leetcode.connect_calls == []
    assert "username" in _output(capsys).lower()


def test_cli_connect_validation_failure_exits_nonzero(capsys, leetcode):
    leetcode.connect_error = ValueError("LeetCode account 'ghost' could not be validated.")

    with pytest.raises(SystemExit) as excinfo:
        main(["leetcode", "connect", "ghost"])

    assert excinfo.value.code == 1
    assert "could not be validated" in _output(capsys)
    assert leetcode.is_connected() is False, "a failed connect must never leave a connection"


def test_cli_connect_scrubs_secrets(capsys, leetcode):
    leetcode.connect_error = LeetCodeAccountError(f"rejected; Cookie: {SECRET_COOKIE}")

    with pytest.raises(SystemExit):
        main(["leetcode", "connect", "bob"])

    assert "FAKE_SESSION_VALUE_123" not in _output(capsys)


# ─────────────────────────────────────────────────────────────────────────────
# sync
# ─────────────────────────────────────────────────────────────────────────────


def test_cli_sync_success_exits_zero(capsys, leetcode):
    leetcode.status_value = LeetCodeAccountStatus(connected=True, username="bob")
    leetcode.sync_result = _sync()

    with pytest.raises(SystemExit) as excinfo:
        main(["leetcode", "sync"])

    assert excinfo.value.code == 0
    out = _output(capsys)
    assert "succeeded" in out
    assert "Imported: 3" in out
    assert "recent-window" in out


def test_cli_sync_partial_exits_two(capsys, leetcode):
    leetcode.status_value = LeetCodeAccountStatus(connected=True, username="bob")
    leetcode.sync_result = _sync(
        status=SyncState.PARTIAL, records_added=2, records_failed=1, error_message="profile fetch failed"
    )

    with pytest.raises(SystemExit) as excinfo:
        main(["leetcode", "sync"])

    assert excinfo.value.code == 2, "PARTIAL is not SUCCESS and must not exit 0"
    out = _output(capsys)
    assert "partially" in out
    assert "Failed: 1" in out


def test_cli_sync_failure_exits_nonzero(capsys, leetcode):
    leetcode.status_value = LeetCodeAccountStatus(connected=True, username="bob")
    leetcode.sync_result = _sync(status=SyncState.FAILED, records_added=0, error_message="network down")

    with pytest.raises(SystemExit) as excinfo:
        main(["leetcode", "sync"])

    assert excinfo.value.code == 1
    assert "failed" in _output(capsys).lower()


def test_cli_sync_when_not_connected_exits_nonzero(capsys, leetcode):
    with pytest.raises(SystemExit) as excinfo:
        main(["leetcode", "sync"])

    assert excinfo.value.code == 1
    assert "not connected" in _output(capsys)
    assert leetcode.sync_calls == []


def test_cli_sync_when_the_surface_raises_exits_nonzero(capsys, leetcode):
    """An exception escaping the surface is reported safely, never as a traceback."""
    leetcode.status_value = LeetCodeAccountStatus(connected=True, username="bob")
    leetcode.sync_error = RuntimeError(f"transport broke; Cookie: {SECRET_COOKIE}")

    with pytest.raises(SystemExit) as excinfo:
        main(["leetcode", "sync"])

    assert excinfo.value.code == 1
    out = _output(capsys)
    assert "could not complete" in out
    assert "FAKE_SESSION_VALUE_123" not in out


def test_cli_sync_forwards_limit(leetcode):
    leetcode.status_value = LeetCodeAccountStatus(connected=True, username="bob")
    leetcode.sync_result = _sync()

    with pytest.raises(SystemExit):
        main(["leetcode", "sync", "--limit", "7"])

    assert leetcode.sync_calls == [7]


def test_cli_sync_prints_coverage_and_unavailable_fields(capsys, leetcode):
    leetcode.status_value = LeetCodeAccountStatus(connected=True, username="bob")
    leetcode.sync_result = _sync(
        status=SyncState.SUCCESS,
        details={
            "coverage": "recent-window",
            "window_limit": 20,
            "records_in_window": 20,
            "window_truncated": True,
            "gap_detected": True,
            "unavailable_fields": ["code", "runtime_ms", "memory_mb"],
        },
    )

    with pytest.raises(SystemExit):
        main(["leetcode", "sync"])

    out = _output(capsys)
    assert "recent-window" in out
    assert "code" in out and "memory_mb" in out


# ─────────────────────────────────────────────────────────────────────────────
# status
# ─────────────────────────────────────────────────────────────────────────────


def test_cli_status_when_connected_exits_zero(capsys, leetcode):
    leetcode.status_value = LeetCodeAccountStatus(
        connected=True,
        username="bob",
        display_name="Bob",
        sync_state=SyncState.SUCCESS,
        records_imported=5,
        records_skipped=2,
        records_failed=0,
        records_discovered=7,
        solved_all=42,
        solved_easy=20,
        solved_medium=15,
        solved_hard=7,
        coverage="recent-window",
        window_limit=20,
        records_in_window=7,
        gap_detected=False,
        unavailable_fields=["code", "runtime_ms", "memory_mb"],
    )

    with pytest.raises(SystemExit) as excinfo:
        main(["leetcode", "status"])

    assert excinfo.value.code == 0
    out = _output(capsys)
    assert "@bob" in out
    assert "Success" in out
    assert "imported=5" in out
    assert "recent-window" in out
    assert "Window limit" in out
    assert "no source code, runtime or memory" in out or "source code" in out


def test_cli_status_when_not_connected_exits_nonzero(capsys, leetcode):
    with pytest.raises(SystemExit) as excinfo:
        main(["leetcode", "status"])

    assert excinfo.value.code == 1
    assert "not connected" in _output(capsys)


def test_cli_status_shows_gap_explanation(capsys):
    console = MagicMock()
    status = LeetCodeAccountStatus(
        connected=True,
        username="bob",
        coverage="recent-window",
        window_limit=20,
        records_in_window=20,
        gap_detected=True,
        unavailable_fields=["code"],
    )
    render_leetcode_status(console, status)

    printed = " ".join(str(call.args[0]) for call in console.print.call_args_list)
    assert "Gap" in printed
    assert "cannot be recovered" in printed


def test_cli_status_omits_counts_when_never_synced(capsys):
    console = MagicMock()
    status = LeetCodeAccountStatus(connected=True, username="bob")
    render_leetcode_status(console, status)

    printed = " ".join(str(call.args[0]) for call in console.print.call_args_list)
    assert "Last successful" in printed
    assert "Never" in printed
    # No fabricated counts: nothing was reported, so nothing is shown as a number.
    assert "imported=None" not in printed


# ─────────────────────────────────────────────────────────────────────────────
# disconnect
# ─────────────────────────────────────────────────────────────────────────────


def test_cli_disconnect_preserves_history(capsys, leetcode):
    leetcode.status_value = LeetCodeAccountStatus(connected=True, username="bob")

    with pytest.raises(SystemExit) as excinfo:
        main(["leetcode", "disconnect"])

    assert excinfo.value.code == 0
    assert leetcode.disconnect_count == 1
    out = _output(capsys)
    assert "disconnected" in out
    assert "preserved" in out


def test_cli_disconnect_when_not_connected_is_a_clean_noop(capsys, leetcode):
    with pytest.raises(SystemExit) as excinfo:
        main(["leetcode", "disconnect"])

    assert excinfo.value.code == 0
    assert "nothing to disconnect" in _output(capsys)


def test_cli_disconnect_failure_exits_nonzero(capsys, leetcode):
    leetcode.status_value = LeetCodeAccountStatus(connected=True, username="bob")
    leetcode.disconnect_error = RuntimeError(f"store is read-only; Cookie: {SECRET_COOKIE}")

    with pytest.raises(SystemExit) as excinfo:
        main(["leetcode", "disconnect"])

    assert excinfo.value.code == 1
    assert "Could not disconnect" in _output(capsys)
    assert "FAKE_SESSION_VALUE_123" not in _output(capsys)


# ─────────────────────────────────────────────────────────────────────────────
# Surface hygiene
# ─────────────────────────────────────────────────────────────────────────────


def test_cli_never_uses_the_low_level_client():
    """The command path must reach LeetCode only through the service surface."""
    source = inspect.getsource(cli_main)
    for forbidden in ("LeetCodeSyncEngine(", "LeetCodeClient(", "fetch_user_submissions", "account_service"):
        assert forbidden not in source, f"CLI must not use low-level LeetCode plumbing: {forbidden!r}"
