"""Phase D — Streamlit UI tests for the LeetCode account/sync surface.

The Settings page must reach LeetCode only through ``service.leetcode``. These
tests drive the real page through Streamlit's own ``AppTest`` runner (no browser,
no network) plus direct unit tests of the page's pure formatting helpers.
"""

import inspect
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from streamlit.testing.v1 import AppTest

from codememory.app.pages import settings_view
from codememory.core.service import CodeMemoryService
from codememory.connectors.account.models import SyncState, SyncStatus
from codememory.connectors.leetcode.scheduler import AutosyncStatus
from codememory.connectors.leetcode.service import LeetCodeAccountError, LeetCodeAccountStatus

SECRET_COOKIE = "LEETCODE_SESSION=FAKE_SESSION_VALUE_123"

PAGE_RUNNER = "from codememory.app.pages import settings_view\nsettings_view.render_settings_page()\n"


class FakeLeetCode:
    """Stand-in for the ``service.leetcode`` surface, recording every call."""

    def __init__(self) -> None:
        self.connect_calls: list[str] = []
        self.connect_error: Exception | None = None
        self.sync_calls: list = []
        self.sync_result: SyncStatus | None = None
        self.sync_error: Exception | None = None
        self.status_value = LeetCodeAccountStatus()
        self.disconnect_count = 0
        self.disconnect_error: Exception | None = None
        # History imported before the account was connected.
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


class FakeAutosync:
    """Stand-in for ``service.autosync``; auto-sync is off by default in tests.

    ``sync_now`` delegates to the stubbed LeetCode surface, so a test still
    controls the outcome of the page's manual sync through ``FakeLeetCode``.
    """

    interval_seconds = 3600

    def __init__(self, leetcode: "FakeLeetCode") -> None:
        self._leetcode = leetcode
        self.ensure_running_calls = 0
        self.sync_now_calls = 0

    def ensure_running(self) -> None:
        self.ensure_running_calls += 1

    def status(self):
        return AutosyncStatus(
            enabled=False,
            interval_seconds=self.interval_seconds,
            running=False,
            last_run_at=None,
            next_run_at=None,
            waiting_for_account=False,
            last_error=None,
        )

    def set_enabled(self, enabled: bool) -> None:
        pass

    def set_interval(self, seconds):
        return self.interval_seconds

    def sync_now(self, limit=None, *, block=False) -> SyncStatus:
        self.sync_now_calls += 1
        return self._leetcode.sync(limit)


@pytest.fixture
def page(monkeypatch, tmp_path: Path):
    """Return a helper that runs the Settings page against a stubbed surface."""

    def run(**status_overrides) -> tuple[AppTest, FakeLeetCode]:
        leetcode = FakeLeetCode()
        if status_overrides:
            leetcode.status_value = LeetCodeAccountStatus(**status_overrides)
        service = SimpleNamespace(
            leetcode=leetcode, history=leetcode.history, autosync=FakeAutosync(leetcode)
        )
        monkeypatch.setattr(settings_view, "get_service", lambda: service)

        runner = tmp_path / "run_settings_page.py"
        runner.write_text(PAGE_RUNNER, encoding="utf-8")
        return AppTest.from_file(str(runner)), leetcode

    return run


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


def _all_text(app: AppTest) -> str:
    """Concatenate everything the page rendered, for content assertions."""
    chunks: list[str] = []
    for kind in ("markdown", "success", "warning", "error", "info", "caption"):
        for element in getattr(app, kind):
            chunks.append(element.value or "")
    return "\n".join(chunks)


# ─────────────────────────────────────────────────────────────────────────────
# Surface hygiene — no low-level LeetCode plumbing in the UI
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "module_path",
    [
        "codememory.app.pages.settings_view",
        "codememory.app.pages.dashboard_view",
        "codememory.app.app",
    ],
)
def test_ui_modules_do_not_touch_low_level_leetcode(module_path):
    """UI code reaches LeetCode only through the service status/sync surface."""
    module = __import__(module_path, fromlist=["__name__"])
    source = inspect.getsource(module)
    for forbidden in ("LeetCodeSyncEngine", "LeetCodeClient", "AccountService", "connect_account("):
        assert forbidden not in source, f"{module_path} must not use low-level LeetCode plumbing: {forbidden!r}"


def test_settings_view_does_not_import_the_sync_engine():
    assert "LeetCodeSyncEngine" not in dir(settings_view)
    assert "safe_error_message" in dir(settings_view), "errors must be scrubbed before display"


# ─────────────────────────────────────────────────────────────────────────────
# Not-connected state + connect
# ─────────────────────────────────────────────────────────────────────────────


def test_not_connected_shows_username_only_form(page):
    app, leetcode = page()
    app.run()

    assert app.exception == []
    username_inputs = [t for t in app.text_input if t.key == "lc_username_input"]
    assert len(username_inputs) == 1
    assert any(b.key == "btn_connect_account" for b in app.button)

    # The form must not request anything but a public username.
    help_text = (username_inputs[0].proto.help or "").lower()
    for forbidden in ("password", "cookie", "token", "session"):
        assert forbidden not in help_text or "no password" in help_text


def test_connect_success_renders_connected_account(page):
    app, leetcode = page()
    app.run()

    app.text_input("lc_username_input").input("neal_wu")
    app.button("btn_connect_account").click().run()

    assert app.exception == []
    assert leetcode.connect_calls == ["neal_wu"]
    assert any("Connected" in (s.value or "") for s in app.success)
    assert any("@neal_wu" in (m.value or "") for m in app.markdown)
    assert any(b.key == "btn_disconnect" for b in app.button), "connected state offers disconnect"


def test_connect_failure_is_shown_and_keeps_account_disconnected(page):
    app, leetcode = page()
    leetcode.connect_error = ValueError("LeetCode account 'ghost' could not be validated.")
    app.run()

    app.text_input("lc_username_input").input("ghost")
    app.button("btn_connect_account").click().run()

    assert app.exception == []
    assert any("could not be validated" in (e.value or "") for e in app.error)
    # No false connected state: the form is still showing.
    assert any(b.key == "btn_connect_account" for b in app.button)
    assert not any(b.key == "btn_disconnect" for b in app.button)


def test_connect_error_message_is_scrubbed(page):
    app, leetcode = page()
    leetcode.connect_error = LeetCodeAccountError(f"rejected; Cookie: {SECRET_COOKIE}")
    app.run()

    app.text_input("lc_username_input").input("bob")
    app.button("btn_connect_account").click().run()

    assert "FAKE_SESSION_VALUE_123" not in _all_text(app)


def test_connect_requires_a_username(page):
    app, leetcode = page()
    app.run()

    app.button("btn_connect_account").click().run()

    assert any("valid LeetCode username" in (e.value or "") for e in app.error)
    assert leetcode.connect_calls == []


@pytest.fixture
def real_page(monkeypatch, tmp_path):
    """Run the real Settings page against a real ``CodeMemoryService``.

    Unlike :func:`page`, this does not stub ``service.leetcode``: it exercises
    the whole persistence path the UI actually takes. The LeetCode transport is
    mocked at the client boundary, and the process directory is moved to a
    scratch tree so the page's relative ``data`` path can never reach the
    developer's own data.
    """

    def run() -> tuple[AppTest, CodeMemoryService]:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            "codememory.connectors.leetcode.client.LeetCodeClient.fetch_user_profile",
            lambda self, username: {
                "username": username,
                "real_name": username.title(),
                "user_avatar": "https://leetcode.com/a.png",
                "solved_all": 1,
                "solved_easy": 1,
                "solved_medium": 0,
                "solved_hard": 0,
                "ranking": 999,
            },
        )
        service = CodeMemoryService()
        monkeypatch.setattr(settings_view, "get_service", lambda: service)

        runner = tmp_path / "run_settings_page.py"
        runner.write_text(PAGE_RUNNER, encoding="utf-8")
        return AppTest.from_file(str(runner)), service

    return run


def test_connect_persists_after_the_data_tree_was_cleared(real_page):
    """The reported UI failure: connecting after "Clear All Data" rebuilt data/.

    The page's ``service.leetcode`` surface is cached for the process, so its
    account store directory disappears underneath it when the data tree is
    rebuilt. Submitting a valid username must reconnect, not surface
    ``[Errno 2] No such file or directory: 'data\\accounts\\...'``.
    """
    app, service = real_page()
    app.run()
    assert app.exception == []

    store_dir = service.base_dir / "accounts"
    assert store_dir.is_dir(), "the lazy surface created its account store"

    # What the "Clear All Data" action leaves behind: data/ gone, then rebuilt
    # as an empty top-level directory only.
    import shutil

    shutil.rmtree(service.base_dir)
    service.base_dir.mkdir(parents=True, exist_ok=True)
    assert not store_dir.exists()

    app.text_input("lc_username_input").input("jaypatil1229")
    app.button("btn_connect_account").click().run()

    assert app.exception == []
    account_file = store_dir / "account_connections.json"
    assert account_file.is_file()
    stored = json.loads(account_file.read_text(encoding="utf-8"))
    assert stored["leetcode"]["username"] == "jaypatil1229"
    # The rerun after a successful connect renders the connected account.
    assert any("@jaypatil1229" in (m.value or "") for m in app.markdown)


# ─────────────────────────────────────────────────────────────────────────────
# Connected status rendering
# ─────────────────────────────────────────────────────────────────────────────


def _connected_status(**overrides) -> dict:
    base = dict(
        connected=True,
        username="neal_wu",
        display_name="Neal Wu",
        sync_state=SyncState.SUCCESS,
        last_attempted_sync=datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc),
        last_successful_sync=datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc),
        records_discovered=7,
        records_imported=5,
        records_skipped=2,
        records_failed=0,
        coverage="recent-window",
        window_limit=20,
        records_in_window=7,
        window_truncated=False,
        gap_detected=False,
        unavailable_fields=["code", "runtime_ms", "memory_mb"],
        solved_all=42,
        solved_easy=20,
        solved_medium=15,
        solved_hard=7,
    )
    base.update(overrides)
    return base


def test_connected_status_renders_every_required_field(page):
    app, _ = page(**_connected_status())
    app.run()

    text = _all_text(app)
    assert "neal_wu" in text
    assert "Success" in text
    assert "Sep 01, 2026 12:00 UTC" in text
    assert "Imported: 5" in text
    assert "Skipped: 2" in text
    assert "recent-window" in text
    assert "Window limit" in text or "Window limit" in text
    assert "Records in window" in text
    assert "no source code, runtime or memory" in text


def test_connected_status_shows_progress_metrics(page):
    app, _ = page(**_connected_status())
    app.run()

    assert [(m.label, str(m.value)) for m in app.metric] == [
        ("Total Solved", "42"),
        ("Easy", "20"),
        ("Medium", "15"),
        ("Hard", "7"),
    ]


def test_sync_failure_state_is_visually_distinct(page):
    app, _ = page(**_connected_status(sync_state=SyncState.FAILED, last_error="network down"))
    app.run()

    text = _all_text(app)
    assert "Failed" in text
    assert "network down" in text


def test_sync_partial_state_is_visually_distinct(page):
    app, _ = page(**_connected_status(sync_state=SyncState.PARTIAL, records_failed=1, records_imported=2))
    app.run()

    text = _all_text(app)
    assert "Partial" in text
    assert "Failed: 1" in text


def test_gap_detection_gets_an_honest_explanation(page):
    app, _ = page(**_connected_status(gap_detected=True))
    app.run()

    warnings = [w.value or "" for w in app.warning]
    assert any("Gap detected" in w for w in warnings)
    assert any("cannot be recovered" in w for w in warnings), (
        "the UI must say the missing range is unreachable, not that it will be fetched"
    )


def test_unavailable_fields_are_never_implied_as_synced(page):
    app, _ = page(**_connected_status())
    app.run()

    text = _all_text(app)
    assert "source code" in text
    assert "runtime" in text
    assert "memory" in text
    assert "no source code, runtime or memory" in text


def test_counts_are_absent_when_never_synced(page):
    """No sync yet ⇒ no fabricated numbers, only the honest connected state."""
    app, _ = page(connected=True, username="neal_wu", display_name="Neal Wu")
    app.run()

    text = _all_text(app)
    assert "neal_wu" in text
    assert "Idle" in text
    assert "Never" in text
    assert "Imported:" not in text
    assert not list(app.metric)


# ─────────────────────────────────────────────────────────────────────────────
# Sync action
# ─────────────────────────────────────────────────────────────────────────────


def test_sync_success_renders_success_message(page):
    app, leetcode = page(**_connected_status())
    leetcode.sync_result = _sync()
    app.run()

    app.button("btn_sync_now").click().run()

    assert app.exception == []
    assert leetcode.sync_calls == [None]
    assert any("Sync complete" in (s.value or "") for s in app.success)


def test_sync_partial_renders_a_warning(page):
    app, leetcode = page(**_connected_status())
    leetcode.sync_result = _sync(
        status=SyncState.PARTIAL, records_added=2, records_failed=1, error_message="profile fetch failed"
    )
    app.run()

    app.button("btn_sync_now").click().run()

    warnings = [w.value or "" for w in app.warning]
    assert any("Partial sync" in w for w in warnings)
    assert any("Failed: 1" in w for w in warnings)
    assert not any("Sync complete" in (s.value or "") for s in app.success)


def test_sync_failure_renders_an_error(page):
    app, leetcode = page(**_connected_status())
    leetcode.sync_result = _sync(status=SyncState.FAILED, records_added=0, error_message="network down")
    app.run()

    app.button("btn_sync_now").click().run()

    errors = [e.value or "" for e in app.error]
    assert any("Sync failed" in e for e in errors)
    assert "network down" in " ".join(errors)


def test_sync_gap_notice_is_attached_to_the_outcome(page):
    app, leetcode = page(**_connected_status(gap_detected=True))
    leetcode.sync_result = _sync(details={
        "coverage": "recent-window",
        "window_limit": 20,
        "records_in_window": 20,
        "window_truncated": True,
        "gap_detected": True,
        "unavailable_fields": ["code", "runtime_ms", "memory_mb"],
    })
    app.run()

    app.button("btn_sync_now").click().run()

    warnings = [w.value or "" for w in app.warning]
    assert any("Gap detected" in w and "cannot be recovered" in w for w in warnings)


def test_sync_when_not_connected_is_an_error_not_a_success(page):
    app, leetcode = page()
    leetcode.sync_result = _sync()  # would look successful, but nothing is connected
    app.run()

    assert not any(b.key == "btn_sync_now" for b in app.button)


# ─────────────────────────────────────────────────────────────────────────────
# Disconnect
# ─────────────────────────────────────────────────────────────────────────────


def test_disconnect_returns_to_the_connect_form_and_preserves_history(page):
    app, leetcode = page(**_connected_status())
    app.run()

    app.button("btn_disconnect").click().run()

    assert app.exception == []
    assert leetcode.disconnect_count == 1
    assert any("disconnected" in (i.value or "").lower() for i in app.info)
    assert any("preserved" in (i.value or "") for i in app.info), (
        "the UI must state that imported history survives disconnect"
    )
    # Back to the not-connected state.
    assert any(b.key == "btn_connect_account" for b in app.button)
    assert not any(b.key == "btn_disconnect" for b in app.button)
    # History untouched by the disconnect path.
    assert leetcode.history == ["two-sum", "3sum"]


def test_disconnect_failure_is_reported_without_crashing_the_page(page):
    """A failing disconnect becomes an error message, not an unhandled exception."""
    app, leetcode = page(**_connected_status())
    leetcode.disconnect_error = LeetCodeAccountError(f"store is read-only; Cookie: {SECRET_COOKIE}")
    app.run()

    app.button("btn_disconnect").click().run()

    assert app.exception == []
    assert leetcode.disconnect_count == 1
    errors = [e.value or "" for e in app.error]
    assert any("read-only" in e for e in errors)
    assert "FAKE_SESSION_VALUE_123" not in _all_text(app)
    # Still connected: the failure must not look like a successful disconnect.
    assert any(b.key == "btn_disconnect" for b in app.button)


def test_reconnect_after_disconnect_keeps_the_form_available(page):
    app, leetcode = page(**_connected_status())
    app.run()
    app.button("btn_disconnect").click().run()

    app.text_input("lc_username_input").input("neal_wu")
    app.button("btn_connect_account").click().run()

    assert app.exception == []
    assert leetcode.connect_calls == ["neal_wu"]
    assert any(b.key == "btn_disconnect" for b in app.button)


# ─────────────────────────────────────────────────────────────────────────────
# Pure formatting helpers
# ─────────────────────────────────────────────────────────────────────────────


def test_sync_result_message_classifies_each_state():
    ok = _sync()
    style, message = settings_view._sync_result_message(ok)
    assert style == "success" and "Sync complete" in message

    partial = _sync(status=SyncState.PARTIAL, records_failed=1, error_message="boom")
    style, message = settings_view._sync_result_message(partial)
    assert style == "warning" and "Partial sync" in message and "boom" in message

    failed = _sync(status=SyncState.FAILED, error_message="down")
    style, message = settings_view._sync_result_message(failed)
    assert style == "error" and "Sync failed" in message


def test_gap_explanation_only_when_detected():
    gapped = LeetCodeAccountStatus(connected=True, gap_detected=True)
    assert settings_view._gap_explanation_for(gapped) is not None
    assert "cannot be recovered" in settings_view._gap_explanation_for(gapped)

    clean = LeetCodeAccountStatus(connected=True, gap_detected=False)
    assert settings_view._gap_explanation_for(clean) is None


def test_unavailable_fields_note():
    status = LeetCodeAccountStatus(connected=True, unavailable_fields=["code", "runtime_ms", "memory_mb"])
    note = settings_view._unavailable_fields_note(status)
    assert note is not None
    assert "no source code, runtime or memory" in note

    assert settings_view._unavailable_fields_note(LeetCodeAccountStatus(connected=True)) is None


def test_fmt_timestamp_handles_missing_values():
    assert settings_view._fmt_timestamp(None) == "Never"
    naive = datetime(2026, 9, 1, 12, 0)
    assert settings_view._fmt_timestamp(naive).endswith("UTC")
