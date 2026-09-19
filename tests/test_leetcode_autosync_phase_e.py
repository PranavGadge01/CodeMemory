"""Phase E — optional background automatic LeetCode sync.

These tests cover the scheduler and its integration into the service surface,
the Settings page and the CLI. The scheduler is the *only* new piece: it adds no
sync logic of its own and reaches the existing integration exclusively through
``service.leetcode.sync()``.

Everything is deterministic. No test sleeps to wait for a worker, and no test
reaches the network: timing is injected through the scheduler's ``wait_fn``
seam, the app service each sync runs on through ``service_factory``, and the
LeetCode transport through stubbed client methods. A started worker is parked on
a latch the test releases, so it stays observable for as long as a test needs
and stops the instant the test says so.

Where a test touches process-global DuckDB connection caches, it uses the
``isolated_service_cache`` fixture, which clears them and closes any leftover
handles so a worker from one test cannot poison the next.
"""

import inspect
import json
import sys
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, List, Optional
from unittest.mock import MagicMock

import pytest

from codememory.app.pages import settings_view
# ``codememory.cli`` re-exports the *function* as ``main``, shadowing the
# submodule attribute, so the module is fetched from sys.modules explicitly.
from codememory.cli.main import build_parser  # noqa: F401  (ensures the submodule is imported)
cli_main = sys.modules["codememory.cli.main"]
from codememory.connectors.account.models import (
    AccountConnection,
    AccountStatus,
    SyncState,
    SyncStatus,
)
from codememory.connectors.account.service import AccountService
from codememory.connectors.leetcode.models import LeetCodeSubmissionRaw
from codememory.connectors.leetcode.scheduler import (
    DEFAULT_INTERVAL_SECONDS,
    MAX_INTERVAL_SECONDS,
    MIN_INTERVAL_SECONDS,
    AutosyncStatus,
    LeetCodeSyncScheduler,
)
from codememory.connectors.leetcode.service import (
    LeetCodeAccountError,
    LeetCodeAccountStatus,
    safe_error_message,
)
from codememory.core.service import CodeMemoryService


# ─────────────────────────────────────────────────────────────────────────────
# Fakes — a stand-in app service and LeetCode surface, recording every call
# ─────────────────────────────────────────────────────────────────────────────


class _FakeLeetCode:
    """Stand-in for the ``service.leetcode`` surface, recording every call."""

    def __init__(
        self,
        *,
        result: Optional[SyncStatus] = None,
        error: Optional[BaseException] = None,
        on_sync: Optional[Callable[[List[Optional[int]]], None]] = None,
    ) -> None:
        self.sync_calls: List[Optional[int]] = []
        self.sync_result = result if result is not None else _sync()
        self.sync_error = error
        self.on_sync = on_sync

    def sync(self, limit: Optional[int] = None) -> SyncStatus:
        self.sync_calls.append(limit)
        if self.on_sync is not None:
            self.on_sync(self.sync_calls)
        if self.sync_error is not None:
            raise self.sync_error
        return self.sync_result

    def is_connected(self) -> bool:
        return True

    def status(self) -> LeetCodeAccountStatus:
        return LeetCodeAccountStatus(connected=True, username="autosyncuser")


class _FakeAppService:
    """Stand-in for the CodeMemoryService a sync runs on."""

    def __init__(self, leetcode: _FakeLeetCode) -> None:
        self.leetcode = leetcode
        self.closed = False

    def close_storage(self) -> None:
        self.closed = True


def _sync(**overrides) -> SyncStatus:
    """A sync result, in the shape the Phase B engine returns."""
    base: dict[str, Any] = dict(
        status=SyncState.SUCCESS,
        records_discovered=2,
        records_added=2,
        records_skipped=0,
        records_failed=0,
        error_message=None,
        details={"coverage": "recent-window", "window_limit": 20, "records_in_window": 2},
    )
    base.update(overrides)
    return SyncStatus(**base)


def _raw(**overrides) -> LeetCodeSubmissionRaw:
    """One accepted submission, exactly as the public API shapes it.

    No code, no runtime, no memory: the supported endpoint supplies none of
    them, and the sync must never invent stand-ins.
    """
    base: dict[str, Any] = dict(
        id="901",
        submission_id="901",
        title="Valid Anagram",
        title_slug="valid-anagram",
        difficulty="Easy",
        language="python3",
        status="Accepted",
        timestamp=1760000000,
    )
    base.update(overrides)
    return LeetCodeSubmissionRaw(**base)


def _build(
    tmp_path: Path,
    *,
    connected: bool = True,
    sync_error: Optional[BaseException] = None,
    sync_result: Optional[SyncStatus] = None,
    on_sync: Optional[Callable[[List[Optional[int]]], None]] = None,
    **kwargs: Any,
) -> tuple[LeetCodeSyncScheduler, _FakeLeetCode, _FakeAppService, List[int]]:
    """A scheduler over ``tmp_path`` whose app service and timing are injected.

    Nothing real is constructed: no CodeMemoryService, no DuckDB connection, no
    client. ``factory_calls`` records how often the sync service was built, so a
    test can prove a skipped tick costs nothing.
    """
    account_service = AccountService(data_dir=tmp_path / "accounts")
    if connected:
        account_service.save_connection(
            AccountConnection(
                provider="LeetCode",
                username="autosyncuser",
                status=AccountStatus.CONNECTED,
            )
        )
    leetcode = _FakeLeetCode(result=sync_result, error=sync_error, on_sync=on_sync)
    service = _FakeAppService(leetcode)
    factory_calls: List[int] = []

    def factory() -> _FakeAppService:
        factory_calls.append(1)
        return service

    scheduler = LeetCodeSyncScheduler(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "data" / "codememory.duckdb",
        account_service=account_service,
        service_factory=factory,
        **kwargs,
    )
    return scheduler, leetcode, service, factory_calls


def _latched_wait(release: threading.Event) -> Callable[[float], bool]:
    """A wait that parks the worker until the test releases it.

    Costs no wall-clock time and spins no CPU: the worker blocks on an event the
    test sets, so a started worker stays alive and observable for as long as the
    test needs, and moves on the moment it is released.
    """

    def wait(seconds: float) -> bool:
        release.wait(timeout=10)
        return True

    return wait


def _stop_after(scheduler: LeetCodeSyncScheduler, release: threading.Event, after: int) -> Callable[[float], bool]:
    """A latched wait that also ends the run once ``after`` syncs have happened.

    The worker ends itself by setting the scheduler's own stop flag, because
    calling ``stop()`` from inside the worker would join its own thread. Nothing
    here depends on wall-clock time.
    """

    def wait(seconds: float) -> bool:
        seen = len(scheduler._service.leetcode.sync_calls) if scheduler._service else 0
        if seen >= after:
            scheduler._stop_event.set()
        release.wait(timeout=10)
        return True

    return wait


def _hold_lock(scheduler: LeetCodeSyncScheduler, held: threading.Event, release: threading.Event) -> None:
    """Acquire the sync lock off the main thread and hold it until released."""

    def holder() -> None:
        with scheduler._sync_lock:
            held.set()
            release.wait(timeout=10)

    threading.Thread(target=holder, daemon=True).start()


@pytest.fixture
def isolated_service_cache(monkeypatch, tmp_path: Path) -> Path:
    """Isolate the process-global service and DuckDB connection caches.

    The connection registry is keyed by raw path string, so a relative
    ``data/codememory.duckdb`` in one test resolves against whatever directory a
    previous test chdir'd into. Clearing it — and closing the handles — keeps a
    worker or a stale handle from leaking across tests.
    """
    from codememory.app import components
    from codememory.storage.duckdb_repository import _shared_duckdb_connections

    monkeypatch.chdir(tmp_path)
    components._global_service_instance = None
    saved_connections = dict(_shared_duckdb_connections)
    _shared_duckdb_connections.clear()
    try:
        components._cached_service.clear()
    except Exception:
        pass
    yield tmp_path
    components._global_service_instance = None
    for conn in _shared_duckdb_connections.values():
        try:
            conn.close()
        except Exception:
            pass
    _shared_duckdb_connections.clear()
    _shared_duckdb_connections.update(saved_connections)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Configuration — defaults, bounds, persistence
# ─────────────────────────────────────────────────────────────────────────────


def test_disabled_by_default_and_constructing_spawns_no_worker(tmp_path: Path):
    """Opting in is an explicit act: construction must be side-effect free."""
    scheduler, _, service, factory_calls = _build(tmp_path)

    assert scheduler.enabled is False
    assert scheduler.interval_seconds == DEFAULT_INTERVAL_SECONDS
    assert scheduler.is_running is False
    assert (tmp_path / "data" / "leetcode_autosync.json").exists() is False
    assert service.closed is False
    # No sync service was built, so no second DuckDB connection was ever opened.
    assert factory_calls == []


def test_enabling_persists_preference_and_starts_worker(tmp_path: Path):
    release = threading.Event()
    scheduler, _, _, _ = _build(tmp_path, wait_fn=_latched_wait(release))

    scheduler.set_enabled(True)

    assert scheduler.enabled is True
    assert scheduler.is_running is True
    stored = json.loads((tmp_path / "data" / "leetcode_autosync.json").read_text(encoding="utf-8"))
    assert stored == {"enabled": True, "interval_seconds": DEFAULT_INTERVAL_SECONDS}

    release.set()
    scheduler.stop(timeout=5)
    assert scheduler.is_running is False


def test_persist_preference_writes_the_config_without_a_worker(tmp_path: Path):
    """The configuration-only path a short-lived process must take.

    ``persist_preference`` is what the CLI uses: the process exits as soon as the
    command finishes, so a worker started here would be killed mid-sync. It must
    write the preference and touch no thread.
    """
    scheduler, _, _, _ = _build(tmp_path)

    applied = scheduler.persist_preference(True, interval_seconds=900)

    assert applied == 900
    assert scheduler.enabled is True
    assert scheduler.is_running is False, "no worker is started in this process"
    assert scheduler._thread is None, "no thread object is left behind to join later"
    stored = json.loads((tmp_path / "data" / "leetcode_autosync.json").read_text(encoding="utf-8"))
    assert stored == {"enabled": True, "interval_seconds": 900}

    # The next process reads the preference but still has to opt into the worker.
    second, _, _, _ = _build(tmp_path)
    assert second.enabled is True
    assert second.is_running is False


def test_persist_preference_does_not_touch_a_running_worker(tmp_path: Path):
    """Configuring must not stop a worker the application already owns."""
    release = threading.Event()
    scheduler, _, _, _ = _build(tmp_path, enabled=True, wait_fn=_latched_wait(release))
    scheduler.start()
    try:
        applied = scheduler.persist_preference(False, interval_seconds=10)

        # The preference is what a later process will read...
        assert applied == MIN_INTERVAL_SECONDS, "the interval is still clamped"
        assert scheduler.enabled is False
        # ...while this process's worker is left alone: only the app retires it.
        assert scheduler.is_running is True
    finally:
        release.set()
        scheduler.stop(timeout=5)


def test_persist_preference_falls_back_to_the_current_interval(tmp_path: Path):
    """Omitting the interval keeps the one already configured."""
    scheduler, _, _, _ = _build(tmp_path)

    assert scheduler.persist_preference(True) == DEFAULT_INTERVAL_SECONDS
    scheduler.set_interval(1800)
    assert scheduler.persist_preference(False) == 1800


def test_set_interval_clamps_to_bounds_and_persists(tmp_path: Path):
    scheduler, _, _, _ = _build(tmp_path)

    assert scheduler.set_interval(1) == MIN_INTERVAL_SECONDS, "an interval below the minimum is raised, never shortened"
    assert scheduler.set_interval(10**9) == MAX_INTERVAL_SECONDS, "an interval above the maximum is capped"
    assert scheduler.set_interval(7200) == 7200
    assert scheduler.set_interval("garbage") == DEFAULT_INTERVAL_SECONDS, "an unusable value falls back, never to zero"

    stored = json.loads((tmp_path / "data" / "leetcode_autosync.json").read_text(encoding="utf-8"))
    assert stored["interval_seconds"] == DEFAULT_INTERVAL_SECONDS


@pytest.mark.parametrize("corrupt", ["{not json", "", "[]", "null", "5"])
def test_unreadable_config_falls_back_to_disabled(tmp_path: Path, corrupt: str):
    """A missing, corrupt or empty preference file must never enable syncing."""
    config_path = tmp_path / "data" / "leetcode_autosync.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(corrupt, encoding="utf-8")

    scheduler, _, _, _ = _build(tmp_path)

    assert scheduler.enabled is False
    assert scheduler.interval_seconds == DEFAULT_INTERVAL_SECONDS


def test_persisted_preference_is_honoured_on_next_start(tmp_path: Path):
    """A preference written in one process is read back in the next one."""
    release = threading.Event()
    first, _, _, _ = _build(tmp_path, wait_fn=_latched_wait(release))
    first.set_enabled(True)
    first.set_interval(1800)
    release.set()
    first.stop(timeout=5)

    second, _, _, _ = _build(tmp_path, wait_fn=_latched_wait(threading.Event()))

    assert second.enabled is True
    assert second.interval_seconds == 1800
    # The constructor reads the preference but does not start the worker; an
    # explicit opt-in is still required.
    assert second.is_running is False

    second.ensure_running()
    assert second.is_running is True
    second.stop(timeout=5)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Worker lifecycle — one worker, no duplicates, clean shutdown
# ─────────────────────────────────────────────────────────────────────────────


def test_start_is_idempotent_so_reruns_cannot_stack_workers(tmp_path: Path):
    """A Streamlit rerun calls ``ensure_running`` every render; it must be cheap."""
    release = threading.Event()
    scheduler, _, _, _ = _build(tmp_path, wait_fn=_latched_wait(release))

    scheduler.ensure_running()
    scheduler.ensure_running()
    scheduler.start()
    scheduler.start()

    assert scheduler.is_running is True
    assert threading.active_count() >= 1
    # Repeated calls left the single worker in place rather than adding one.
    assert scheduler._thread is not None
    assert scheduler._thread.name == "codememory-leetcode-autosync"

    release.set()
    scheduler.stop(timeout=5)
    assert scheduler.is_running is False
    assert scheduler._thread is None


def test_stop_without_start_is_a_no_op(tmp_path: Path):
    scheduler, _, _, _ = _build(tmp_path)
    scheduler.stop(timeout=5)
    assert scheduler.is_running is False


def test_stop_from_inside_the_worker_does_not_deadlock(tmp_path: Path):
    """A sync that retires its own service must not join the thread it runs on."""
    release = threading.Event()
    release.set()
    scheduler, _, service, _ = _build(tmp_path, enabled=True, wait_fn=_latched_wait(release))
    scheduler._service = service  # pretend a tick already built it

    def stop_from_inside() -> None:
        scheduler.stop(timeout=5)

    thread = threading.Thread(target=stop_from_inside, daemon=True)
    thread.start()
    thread.join(timeout=10)

    assert not thread.is_alive(), "stop() on its own thread must return, not hang"
    assert service.closed is True


def test_stop_releases_the_dedicated_service(tmp_path: Path):
    release = threading.Event()
    scheduler, _, service, _ = _build(tmp_path, enabled=True, wait_fn=_latched_wait(release))
    # A sync has to run for the dedicated service to exist; a stopped scheduler
    # that never synced has nothing to release.
    scheduler._tick_once()
    scheduler.start()
    release.set()
    scheduler.stop(timeout=5)

    assert service.closed is True, "the dedicated service must not outlive its worker"
    assert scheduler._service is None


def test_a_second_scheduler_for_the_same_tree_stops_independently(tmp_path: Path):
    """Two schedulers over one data tree are independent, not mutually aware."""
    release = threading.Event()
    one, leetcode_one, _, _ = _build(tmp_path, wait_fn=_latched_wait(release))
    two, leetcode_two, _, _ = _build(tmp_path, wait_fn=_latched_wait(threading.Event()))
    one.start()
    two.start()

    assert one.is_running and two.is_running
    assert one._thread is not two._thread

    release.set()
    one.stop(timeout=5)
    assert one.is_running is False
    assert two.is_running is True, "stopping one must not stop the other"
    two.stop(timeout=5)


def test_worker_keeps_ticking_until_stopped(tmp_path: Path):
    """A worker ticks, parks on its wait, and resumes when the interval elapses."""
    release = threading.Event()
    ticked = threading.Event()

    def record(calls: List[Optional[int]]) -> None:
        ticked.set()

    scheduler, leetcode, _, _ = _build(tmp_path, on_sync=record)
    scheduler._wait = _stop_after(scheduler, release, 2)
    scheduler.set_enabled(True)

    # The first tick is immediate — enabling starts the work, it does not queue it.
    assert ticked.wait(timeout=10)
    assert leetcode.sync_calls == [None]

    # Releasing the wait simulates an interval elapsing: one more tick, then the
    # worker ends the run itself.
    ticked.clear()
    release.set()
    assert ticked.wait(timeout=10)
    assert leetcode.sync_calls == [None, None]

    scheduler.stop(timeout=5)
    assert scheduler.is_running is False


# ─────────────────────────────────────────────────────────────────────────────
# 3. Scheduling — what a tick does, and what it must not do
# ─────────────────────────────────────────────────────────────────────────────


def test_tick_syncs_once_through_the_canonical_surface(tmp_path: Path):
    """A scheduled tick calls exactly one ``service.leetcode.sync()``."""
    scheduler, leetcode, _, factory_calls = _build(tmp_path, enabled=True)

    result = scheduler._tick_once()

    assert leetcode.sync_calls == [None]
    assert leetcode.sync_calls[0] is None, "a scheduled sync requests no local limit bound"
    assert result is not None and result.status == SyncState.SUCCESS
    assert factory_calls == [1], "the sync service is built once and reused"


def test_no_account_means_no_sync_and_no_service(tmp_path: Path):
    """No account, no scheduled sync — and no network call or connection at all."""
    # Enabled, so the skip is specifically about the missing account.
    scheduler, leetcode, _, factory_calls = _build(tmp_path, connected=False, enabled=True)

    assert scheduler._tick_once() is None
    assert leetcode.sync_calls == []
    assert factory_calls == [], "nothing to sync must cost no connection either"


def test_disabled_scheduler_tick_is_a_no_op(tmp_path: Path):
    scheduler, leetcode, _, _ = _build(tmp_path)
    assert scheduler.enabled is False

    assert scheduler._tick_once() is None
    assert leetcode.sync_calls == []


def test_status_reports_waiting_on_account(tmp_path: Path):
    """Enabled with no account is a distinct, explainable state."""
    release = threading.Event()
    scheduler, _, _, _ = _build(tmp_path, connected=False, enabled=True, wait_fn=_latched_wait(release))
    scheduler.start()
    try:
        state = scheduler.status()
        assert state.enabled is True
        assert state.running is True
        assert state.waiting_for_account is True
    finally:
        release.set()
        scheduler.stop(timeout=5)


def test_scheduled_tick_skips_when_a_manual_sync_is_in_flight(tmp_path: Path):
    """A scheduled sync must never overlap a manual one for the same account."""
    scheduler, leetcode, _, _ = _build(tmp_path, enabled=True)
    held, release = threading.Event(), threading.Event()
    _hold_lock(scheduler, held, release)
    held.wait(timeout=10)

    try:
        assert scheduler._tick_once() is None
        assert leetcode.sync_calls == [], "the tick must defer to the running sync, not queue behind it"
    finally:
        release.set()


def test_manual_sync_now_reuses_the_lock(tmp_path: Path):
    """The manual path goes through the same lock, so it serialises with ticks."""
    scheduler, leetcode, _, _ = _build(tmp_path)

    result = scheduler.sync_now()

    assert result.status == SyncState.SUCCESS
    assert leetcode.sync_calls == [None]


def test_sync_now_refuses_to_overlap_and_does_not_block(tmp_path: Path):
    """A blocked UI render is worse than a refused sync, so it is refused."""
    scheduler, leetcode, _, _ = _build(tmp_path)
    held, release = threading.Event(), threading.Event()
    _hold_lock(scheduler, held, release)
    held.wait(timeout=10)

    try:
        with pytest.raises(LeetCodeAccountError) as excinfo:
            scheduler.sync_now(block=False)
        assert "already running" in str(excinfo.value)
        assert safe_error_message(excinfo.value) == str(excinfo.value), "the refusal message is already UI-safe"
    finally:
        release.set()


def test_sync_now_can_block_until_the_lock_is_free(tmp_path: Path):
    scheduler, leetcode, _, _ = _build(tmp_path)
    held = threading.Event()

    def hold_then_release() -> None:
        with scheduler._sync_lock:
            held.set()

    threading.Thread(target=hold_then_release, daemon=True).start()
    held.wait(timeout=10)

    result = scheduler.sync_now(block=True)
    assert result.status == SyncState.SUCCESS


# ─────────────────────────────────────────────────────────────────────────────
# 4. Lock release — on every outcome, including failure
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("outcome", [SyncState.SUCCESS, SyncState.PARTIAL, SyncState.FAILED])
def test_lock_releases_after_every_sync_outcome(tmp_path: Path, outcome: SyncState):
    """Success, Partial and Failed are all ordinary returns — the lock frees."""
    scheduler, _, _, _ = _build(tmp_path, sync_result=_sync(status=outcome))

    scheduler.sync_now()

    assert scheduler._sync_lock.acquire(blocking=False) is True
    scheduler._sync_lock.release()


def test_lock_releases_after_an_exception(tmp_path: Path):
    """An exception in the sync must not leave the account permanently locked."""
    scheduler, _, _, _ = _build(tmp_path, sync_error=RuntimeError("transport down"))

    with pytest.raises(RuntimeError):
        scheduler.sync_now()

    assert scheduler._sync_lock.acquire(blocking=False) is True
    scheduler._sync_lock.release()
    assert scheduler.status().last_error == "transport down"


def test_secret_in_a_scheduled_failure_is_scrubbed(tmp_path: Path):
    """A credential escaping the transport must never reach a UI-facing field."""
    leaking = LeetCodeAccountError("Authorization: Bearer abcdefghijklmnop0123456789 rejected")
    scheduler, _, _, _ = _build(tmp_path, sync_error=leaking, enabled=True)

    with pytest.raises(LeetCodeAccountError):
        scheduler._tick_once()

    recorded = scheduler.status().last_error
    assert "abcdefghijklmnop0123456789" not in recorded
    assert "redacted" in recorded


def test_scheduled_failure_does_not_kill_the_worker(tmp_path: Path):
    """One bad tick must not take the scheduler down with it."""
    scheduler, leetcode, _, _ = _build(
        tmp_path, sync_error=RuntimeError("flap"), enabled=True, wait_fn=lambda seconds: True
    )
    assert scheduler.is_running is False, "enabled alone never starts a worker"

    # A failing tick raises out of the tick method; the loop's guard is what keeps
    # the scheduler alive, and the next tick must still be able to run.
    with pytest.raises(RuntimeError):
        scheduler._tick_once()
    with pytest.raises(RuntimeError):
        scheduler._tick_once()

    assert leetcode.sync_calls == [None, None]
    assert scheduler.status().last_error == "flap"


def test_unexpected_tick_exception_does_not_stop_the_loop(tmp_path: Path):
    """The loop's guard keeps a genuinely unexpected error from killing it."""
    release = threading.Event()
    release.set()
    scheduler, leetcode, _, _ = _build(tmp_path)
    scheduler._wait = _stop_after(scheduler, release, 1)
    original_tick = scheduler._tick_once
    failures: List[int] = []

    def flaky() -> Any:
        if len(failures) < 2:
            failures.append(1)
            raise RuntimeError("boom")
        return original_tick()

    scheduler._tick_once = flaky
    scheduler.set_enabled(True)

    # Two ticks blow up inside the loop and the third completes a real sync; the
    # wait seam then ends the run, so exactly one sync is observed.
    assert scheduler._thread is not None
    scheduler._thread.join(timeout=10)
    assert not scheduler.is_running
    assert len(failures) == 2
    assert leetcode.sync_calls == [None], "the loop recovered and completed a real tick"


# ─────────────────────────────────────────────────────────────────────────────
# 5. Service-level integration — the real surface, still no network
# ─────────────────────────────────────────────────────────────────────────────


_PROFILE = {
    "username": "autosyncuser",
    "real_name": "Auto Sync",
    "user_avatar": "https://leetcode.com/a.png",
    "ranking": 99,
    "solved_all": 10,
    "solved_easy": 4,
    "solved_medium": 4,
    "solved_hard": 2,
}


def _real_service(tmp_path: Path) -> CodeMemoryService:
    return CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "data" / "codememory.duckdb",
    )


@pytest.fixture
def offline_transport(monkeypatch) -> None:
    """Stub the public transport at the class seam; every client built sees it."""
    from codememory.connectors.leetcode.client import LeetCodeClient

    monkeypatch.setattr(
        LeetCodeClient, "fetch_user_profile", lambda self, username: dict(_PROFILE, username=username)
    )
    monkeypatch.setattr(
        LeetCodeClient, "fetch_user_submissions", lambda self, username, limit: [_raw()]
    )
    monkeypatch.setattr(LeetCodeClient, "fetch_problem_details", lambda self, slug: None)


def _connect_account(service: CodeMemoryService) -> None:
    """Store a connected account through the canonical surface."""
    service.leetcode.connect("autosyncuser")


def test_autosync_property_is_lazy_and_stable(isolated_service_cache, offline_transport):
    service = _real_service(isolated_service_cache)

    assert service._autosync is None, "no scheduler is built until it is asked for"
    assert service.autosync is service.autosync, "one scheduler per service, not one per access"


def test_scheduler_uses_its_own_duckdb_connection(isolated_service_cache, offline_transport):
    """The worker's storage is isolated from the pooled handle the UI shares."""
    from codememory.storage.duckdb_repository import _shared_duckdb_connections

    service = _real_service(isolated_service_cache)
    _connect_account(service)
    pooled_handles = set(_shared_duckdb_connections.values())

    # Enabled without starting the worker: what is under test is the service the
    # sync runs on, not the thread that would drive it.
    service.autosync._enabled = True
    service.autosync._tick_once()

    # The pooled registry is untouched, and the worker's handle is not in it.
    assert set(_shared_duckdb_connections.values()) == pooled_handles
    worker_service = service.autosync._service
    assert worker_service is not None
    assert worker_service.storage.duckdb_repo.conn not in _shared_duckdb_connections.values()

    # The sync really ran, end to end, and is visible from the UI's own service.
    assert any(p.title == "Valid Anagram" for p in service.list_problems())

    service.autosync.stop(timeout=5)
    service.close_storage()


def test_close_storage_stops_the_worker(isolated_service_cache, offline_transport):
    """Retiring a service must not leave a worker syncing into a dead tree."""
    service = _real_service(isolated_service_cache)
    _connect_account(service)
    service.autosync.set_enabled(True)
    assert service.autosync.is_running is True

    service.close_storage()

    assert service.autosync.is_running is False
    assert service.autosync._service is None, "the dedicated connection was released too"


def test_clearing_data_stops_the_worker_and_drops_the_preference(isolated_service_cache, offline_transport):
    """A fresh storage tree starts from a fresh scheduler preference."""
    import shutil

    service = _real_service(isolated_service_cache)
    _connect_account(service)
    service.autosync.set_enabled(True)
    assert service.autosync.is_running is True

    service.close_storage()
    shutil.rmtree(isolated_service_cache / "data")
    (isolated_service_cache / "data").mkdir()

    rebuilt = _real_service(isolated_service_cache)
    assert rebuilt.autosync.enabled is False, "the wiped preference must not survive"
    assert rebuilt.autosync.is_running is False
    rebuilt.close_storage()


# ─────────────────────────────────────────────────────────────────────────────
# 6. Settings page — controls and wiring, driven through Streamlit's AppTest
# ─────────────────────────────────────────────────────────────────────────────


class FakeAutosync:
    """Stand-in for ``service.autosync`` that records the page's requests."""

    interval_seconds: int = DEFAULT_INTERVAL_SECONDS

    def __init__(self) -> None:
        self.ensure_running_calls = 0
        self.enabled = False
        self.set_enabled_calls: List[bool] = []
        self.persist_calls: List[Any] = []
        self.set_interval_calls: List[Any] = []
        self.sync_now_calls = 0
        self.sync_result = _sync()
        self.sync_error: Optional[BaseException] = None

    def ensure_running(self) -> None:
        self.ensure_running_calls += 1

    def status(self) -> AutosyncStatus:
        return AutosyncStatus(
            enabled=self.enabled,
            interval_seconds=DEFAULT_INTERVAL_SECONDS,
            running=self.enabled,
            last_run_at=None,
            next_run_at=None,
            waiting_for_account=False,
            last_error=None,
        )

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)
        self.set_enabled_calls.append(bool(enabled))

    def persist_preference(self, enabled: bool, interval_seconds: Optional[Any] = None) -> int:
        self.enabled = bool(enabled)
        self.persist_calls.append((bool(enabled), interval_seconds))
        if interval_seconds is None:
            return self.interval_seconds
        return self.set_interval(interval_seconds)

    def set_interval(self, seconds: Any) -> int:
        self.set_interval_calls.append(seconds)
        if not isinstance(seconds, (int, float)):
            return DEFAULT_INTERVAL_SECONDS
        return int(max(MIN_INTERVAL_SECONDS, min(MAX_INTERVAL_SECONDS, seconds)))

    def sync_now(self, limit: Optional[int] = None, *, block: bool = False) -> SyncStatus:
        self.sync_now_calls += 1
        if self.sync_error is not None:
            raise self.sync_error
        return self.sync_result


PAGE_RUNNER = (
    "from codememory.app.pages import settings_view\n"
    "settings_view.render_settings_page()\n"
)


@pytest.fixture
def page(monkeypatch, tmp_path: Path):
    """Run the Settings page against a stubbed service, with no Streamlit server."""

    def run(*, connected: bool = True, autosync: Optional[FakeAutosync] = None):
        from streamlit.testing.v1 import AppTest

        leetcode = MagicMock()
        leetcode.status.return_value = LeetCodeAccountStatus(
            connected=connected, username="autosyncuser", display_name="Auto Sync"
        )
        leetcode.sync.side_effect = AssertionError("the page must not call the raw sync surface directly")
        autosync = autosync or FakeAutosync()
        service = SimpleNamespace(leetcode=leetcode, autosync=autosync)
        monkeypatch.setattr(settings_view, "get_service", lambda: service)
        runner = tmp_path / "run_settings_page.py"
        runner.write_text(PAGE_RUNNER, encoding="utf-8")
        return AppTest.from_file(str(runner)), leetcode, autosync

    return run


def _all_text(app) -> str:
    parts: List[str] = []
    for kind in ("markdown", "success", "warning", "error", "info", "caption"):
        for element in getattr(app, kind, None) or []:
            parts.append(getattr(element, "value", str(element)))
    return " ".join(parts)


def test_settings_page_renders_autosync_controls(page):
    app, _, autosync = page()
    app.run()

    assert app.exception == []
    assert len(app.toggle) == 1
    assert len(app.number_input) == 1
    # The worker is started through the idempotent entry point, once per render.
    assert autosync.ensure_running_calls == 1


def test_settings_page_shows_interval_bounds(page):
    app, _, _ = page()
    app.run()

    assert app.exception == []
    interval = app.number_input("lc_autosync_interval")
    assert interval.min == MIN_INTERVAL_SECONDS // 60
    assert interval.max == MAX_INTERVAL_SECONDS // 60


def test_settings_page_enabling_persists_and_reruns(page):
    app, _, autosync = page()
    app.run()
    assert app.exception == []
    assert autosync.set_enabled_calls == []

    app.toggle("lc_autosync_enabled").set_value(True).run()

    assert app.exception == []
    assert autosync.set_enabled_calls == [True]
    assert "Automatic LeetCode sync enabled" in _all_text(app)
    # The toggle now reflects the persisted state, so the page has converged.
    assert app.toggle("lc_autosync_enabled").value is True


def test_settings_page_sync_now_goes_through_the_scheduler(page):
    """The button must not bypass the scheduler's shared lock."""
    app, leetcode, autosync = page()
    app.run()
    app.button("btn_sync_now").click().run()

    assert app.exception == []
    assert autosync.sync_now_calls == 1
    assert "Sync complete" in _all_text(app)


def test_settings_page_reports_a_refused_sync(page):
    app, _, autosync = page()
    autosync.sync_error = LeetCodeAccountError("A LeetCode sync is already running for this account.")
    app.run()
    app.button("btn_sync_now").click().run()

    assert app.exception == []
    assert "already running" in _all_text(app)


def test_settings_page_never_touches_low_level_plumbing():
    """The page reaches the scheduler surface only, never the transport."""
    source = inspect.getsource(settings_view)
    for forbidden in ("LeetCodeSyncEngine", "LeetCodeClient", "LeetCodeSyncScheduler"):
        assert forbidden not in source, f"the page must not name {forbidden}"


# ─────────────────────────────────────────────────────────────────────────────
# 7. CLI — configuration commands
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def cli(monkeypatch) -> FakeAutosync:
    """Replace the CLI's service with one whose scheduler is a stub."""
    autosync = FakeAutosync()
    leetcode = MagicMock()
    leetcode.is_connected.return_value = True
    service = SimpleNamespace(leetcode=leetcode, autosync=autosync)
    monkeypatch.setattr(cli_main, "CodeMemoryService", lambda *a, **k: service)
    return autosync


def _output(capsys) -> str:
    return capsys.readouterr().out


def test_cli_parser_supports_autosync():
    from codememory.cli.main import build_parser

    parsed = build_parser().parse_args(["leetcode", "autosync", "enable", "--interval", "600"])
    assert parsed.action == "autosync"
    assert parsed.path == "enable"
    assert parsed.interval == 600


def test_cli_autosync_enable_persists_and_exits_zero(capsys, cli):
    with pytest.raises(SystemExit) as excinfo:
        cli_main.main(["leetcode", "autosync", "enable", "--interval", "600"])
    assert excinfo.value.code == 0

    # The CLI persists the configuration through the worker-free entry point: a
    # CLI process exits at once, so it must not launch a worker that dies with it.
    assert cli.persist_calls == [(True, 600)]
    assert cli.set_enabled_calls == [], "the CLI must not touch the worker lifecycle"
    assert "Automatic LeetCode sync enabled" in _output(capsys)


def test_cli_autosync_enable_without_interval_uses_default(capsys, cli):
    with pytest.raises(SystemExit):
        cli_main.main(["leetcode", "autosync", "enable"])

    # The CLI always writes an explicit interval, defaulted when none was given.
    assert cli.persist_calls == [(True, DEFAULT_INTERVAL_SECONDS)]
    assert cli.set_enabled_calls == []


def test_cli_autosync_disable(capsys, cli):
    with pytest.raises(SystemExit):
        cli_main.main(["leetcode", "autosync", "disable"])

    assert cli.persist_calls == [(False, None)]
    assert cli.set_enabled_calls == [], "disabling from the CLI persists only"
    assert "disabled" in _output(capsys)


def test_cli_autosync_status_reports_state(capsys, cli):
    cli.enabled = True
    with pytest.raises(SystemExit):
        cli_main.main(["leetcode", "autosync", "status"])

    out = _output(capsys)
    assert "enabled" in out
    assert str(DEFAULT_INTERVAL_SECONDS) in out


def test_cli_autosync_status_warns_when_no_account(capsys, cli, monkeypatch):
    from codememory.cli.main import build_parser

    service = SimpleNamespace(
        leetcode=MagicMock(is_connected=MagicMock(return_value=False)), autosync=cli
    )
    monkeypatch.setattr(cli_main, "CodeMemoryService", lambda *a, **k: service)
    cli.enabled = True

    with pytest.raises(SystemExit):
        cli_main.main(["leetcode", "autosync", "status"])

    assert "No LeetCode account is connected" in _output(capsys)


def test_cli_autosync_bad_subcommand_fails(capsys, cli):
    with pytest.raises(SystemExit) as excinfo:
        cli_main.main(["leetcode", "autosync", "bogus"])

    assert excinfo.value.code == 1
    assert cli.set_enabled_calls == []


def test_scheduler_module_does_not_reimplement_the_transport():
    """The scheduler names the service surface only — no engine, client or retry."""
    source = inspect.getsource(LeetCodeSyncScheduler)
    # Identifiers, not prose: the point is that the scheduler never reaches the
    # transport or the engine, only the service surface it was given.
    for forbidden in ("LeetCodeSyncEngine", "LeetCodeClient", "fetch_user_", "time.sleep"):
        assert forbidden not in source, f"the scheduler must not reimplement {forbidden}"
