"""Optional background scheduling for LeetCode sync (Phase E).

This module adds *one* capability on top of the existing integration: a worker
thread that periodically calls the canonical sync entry point. It contains no
sync logic of its own — no transport, no retry policy, no pagination, no
watermark handling. Every one of those concerns stays in
:class:`~codememory.connectors.leetcode.sync.LeetCodeSyncEngine`, reached
exclusively through ``service.leetcode.sync()``.

Lifecycle and concurrency guarantees:

* The worker thread is created only when auto-sync is explicitly enabled, and
  only ever one of them (``start()`` is idempotent). A process that never opts
  in never spawns it, and constructing a scheduler is not opting in.
* A single non-reentrant lock serialises every sync for this account —
  scheduled *and* manually triggered — so the two can never overlap. It is
  released on ``Success``, ``Partial``, ``Failed`` and on any exception, via
  ``try/finally``.
* No account connected means no sync attempt and no network call at all; a
  disconnect therefore stops the scheduled traffic without silently rewriting
  the user's preference.
* A failing scheduled sync is logged and the tick ends; the worker stays alive
  for the next interval.
* The worker stops and releases its own storage connection before the service
  it belongs to is retired (notably by "Clear All Data").

Configuration (enabled / interval) is persisted as plain JSON under the data
directory so it survives a restart, and every unreadable or missing file falls
back to the safe default: *disabled*.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from codememory.connectors.account.models import SyncStatus
from codememory.connectors.account.service import AccountService
from codememory.connectors.leetcode.service import (
    LeetCodeAccountError,
    safe_error_message,
)

logger = logging.getLogger(__name__)

PROVIDER = "LeetCode"

# The public recent-submission window shifts slowly, so an hourly default is
# both useful and polite toward the unauthenticated endpoint. The bounds exist
# so a mis-typed interval can never turn auto-sync into a request flood.
DEFAULT_INTERVAL_SECONDS = 3600
MIN_INTERVAL_SECONDS = 300
MAX_INTERVAL_SECONDS = 86400

CONFIG_FILENAME = "leetcode_autosync.json"

_THREAD_NAME = "codememory-leetcode-autosync"


def _clamp_interval(seconds: Any) -> int:
    """Coerce ``seconds`` to an interval inside the allowed bounds.

    An unusable value falls back to the default rather than to zero, because a
    zero interval would mean a worker that never waits between requests.
    """
    try:
        value = int(seconds)
    except (TypeError, ValueError):
        return DEFAULT_INTERVAL_SECONDS
    return max(MIN_INTERVAL_SECONDS, min(MAX_INTERVAL_SECONDS, value))


@dataclass(frozen=True)
class AutosyncConfig:
    """Persisted auto-sync preferences."""

    enabled: bool
    interval_seconds: int


@dataclass(frozen=True)
class AutosyncStatus:
    """UI-ready view of the scheduler's configuration and worker state."""

    enabled: bool
    interval_seconds: int
    running: bool
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
    waiting_for_account: bool
    last_error: Optional[str]


class LeetCodeSyncScheduler:
    """Schedules periodic ``service.leetcode.sync()`` calls on a worker thread.

    Constructing one is side-effect free. Call :meth:`set_enabled` (or
    :meth:`ensure_running`) to start the worker, and :meth:`stop` to end it.
    :meth:`persist_preference` writes the configuration *without* starting a
    worker, which is what a short-lived process such as the CLI must do.
    Manual syncs should go through :meth:`sync_now` so they share the same lock
    as the scheduled ones.
    """

    def __init__(
        self,
        base_dir: str | Path,
        knowledge_dir: str | Path,
        db_path: str | Path,
        *,
        interval_seconds: Optional[int] = None,
        enabled: Optional[bool] = None,
        account_service: Optional[AccountService] = None,
        service_factory: Optional[Callable[[], Any]] = None,
        wait_fn: Optional[Callable[[float], bool]] = None,
    ) -> None:
        self._base_dir = Path(base_dir)
        self._knowledge_dir = Path(knowledge_dir)
        self._db_path = str(db_path)
        self._config_path = self._base_dir / CONFIG_FILENAME

        # Connectivity is probed through the cheap account store rather than by
        # building a full service: no account must ever cost a DuckDB connection
        # or a network call.
        self._account_service = account_service or AccountService(data_dir=self._base_dir / "accounts")
        # The service each sync runs on is built by this factory, and only on
        # first use. The default builds a service with a *dedicated* DuckDB
        # connection: the pooled one the UI thread shares is not safe for
        # concurrent access, while two separate connections to the same file are
        # serialised by DuckDB itself.
        self._service_factory = service_factory or self._default_service_factory
        # Time between ticks. Overridable so tests never have to sleep.
        self._wait = wait_fn or self._default_wait

        self._lifecycle_lock = threading.Lock()
        # Serialises every sync for this account — scheduled and manual alike.
        # Non-reentrant: neither path ever nests an acquire.
        self._sync_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._service: Optional[Any] = None

        stored = self._load_config()
        self._enabled = stored.enabled if enabled is None else bool(enabled)
        self._interval_seconds = _clamp_interval(
            interval_seconds if interval_seconds is not None else stored.interval_seconds
        )
        # In-memory bookkeeping for the status line only: the authoritative
        # record of the last sync lives on the account connection, so a sync run
        # by this worker is visible through ``service.leetcode.status()`` even
        # after a restart.
        self._last_run_at: Optional[datetime] = None
        self._last_error: Optional[str] = None

    # ───────────────────────────────────────────────────────────────────────
    # Configuration
    # ───────────────────────────────────────────────────────────────────────

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def interval_seconds(self) -> int:
        return self._interval_seconds

    def status(self) -> AutosyncStatus:
        """Report configuration and worker state for display."""
        running = self.is_running
        next_run_at = None
        if running and self._last_run_at is not None:
            next_run_at = self._last_run_at + timedelta(seconds=self._interval_seconds)
        return AutosyncStatus(
            enabled=self._enabled,
            interval_seconds=self._interval_seconds,
            running=running,
            last_run_at=self._last_run_at,
            next_run_at=next_run_at,
            # Enabled but no account: the worker is alive and doing nothing but
            # waiting for a connection. Worth telling the user apart from
            # "disabled", because it explains why nothing is syncing.
            waiting_for_account=running and self._enabled and not self._account_service.is_connected(PROVIDER),
            last_error=self._last_error,
        )

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable automatic sync, persist the choice, and apply it.

        Disabling stops the worker; enabling starts it. Persisting means a
        preference set in one process is honoured by the next.

        Processes that cannot host a worker — the CLI, which exits as soon as the
        command finishes — must use :meth:`persist_preference` instead, so the
        choice is written without starting a thread that dies with the process.
        """
        self.persist_preference(enabled)
        if self._enabled:
            self.ensure_running()
        else:
            self.stop()

    def persist_preference(self, enabled: bool, interval_seconds: Optional[Any] = None) -> int:
        """Write the preference (and optionally the interval) without a worker.

        This is ``set_enabled`` for short-lived processes. Nothing is started and
        nothing is stopped here, so no thread in this process outlives the call or
        is killed with the process when it exits. The next long-lived process —
        the web app — reads the file and owns the worker lifecycle itself.

        Returns the interval actually applied, clamped to its bounds, so a caller
        can report the real number back rather than the one that was typed.
        """
        if interval_seconds is not None:
            self._interval_seconds = _clamp_interval(interval_seconds)
        self._enabled = bool(enabled)
        self._save_config()
        return self._interval_seconds

    def set_interval(self, seconds: Any) -> int:
        """Set the sync interval (clamped to its bounds) and persist it.

        Returns the value actually applied, so a caller can show the clamped
        number back to the user instead of the one they typed.
        """
        self._interval_seconds = _clamp_interval(seconds)
        self._save_config()
        return self._interval_seconds

    def ensure_running(self) -> None:
        """Start the worker if it is enabled and not already running.

        Cheap and idempotent, so a UI can call it on every render without ever
        spawning a second worker.
        """
        if self._enabled and not self.is_running:
            self.start()

    # ───────────────────────────────────────────────────────────────────────
    # Worker lifecycle
    # ───────────────────────────────────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        thread = self._thread
        return thread is not None and thread.is_alive()

    def start(self) -> None:
        """Start the worker thread, once, regardless of how often it is called."""
        with self._lifecycle_lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event.clear()
            thread = threading.Thread(target=self._run, name=_THREAD_NAME, daemon=True)
            self._thread = thread
        thread.start()
        logger.info("LeetCode automatic sync worker started (interval: %ss)", self._interval_seconds)

    def stop(self, *, timeout: float = 5.0) -> None:
        """Signal the worker to stop and wait for it, then release its service.

        Safe to call when the worker was never started. If the worker does not
        finish within ``timeout`` (it is mid-sync), its service is left open
        rather than closed out from under a running sync.
        """
        with self._lifecycle_lock:
            thread = self._thread
        self._stop_event.set()
        if thread is None:
            self._close_service()
            return
        # A stop from inside the worker (a sync that retires its own service)
        # must not join the thread it is running on — that is a deadlock.
        if thread is threading.current_thread():
            self._close_service()
            return
        thread.join(timeout=timeout)
        stopped = not thread.is_alive()
        with self._lifecycle_lock:
            if self._thread is thread and stopped:
                self._thread = None
        if stopped:
            self._close_service()
        else:
            logger.warning(
                "LeetCode auto-sync worker did not stop within %.1fs; leaving its service open",
                timeout,
            )

    # ───────────────────────────────────────────────────────────────────────
    # Sync entry points
    # ───────────────────────────────────────────────────────────────────────

    def sync_now(self, limit: Optional[int] = None, *, block: bool = False) -> SyncStatus:
        """Run one sync now, on the shared lock.

        This is the path a manual "Sync Now" should take: it reuses the
        scheduler's dedicated service and, crucially, the same lock the
        scheduled ticks take, so a manual and a scheduled sync can never
        overlap.

        With ``block=False`` (the UI default, which must not stall a render) it
        raises :class:`LeetCodeAccountError` when a sync is already running,
        rather than blocking the caller until it finishes.
        """
        if not self._sync_lock.acquire(blocking=block):
            raise LeetCodeAccountError(
                "A LeetCode sync is already running for this account. "
                "Wait for it to finish before starting another."
            )
        try:
            return self._sync_locked(limit=limit, source="manual")
        finally:
            self._sync_lock.release()

    def _default_service_factory(self) -> Any:
        from codememory.core.service import CodeMemoryService

        return CodeMemoryService(
            base_dir=self._base_dir,
            knowledge_dir=self._knowledge_dir,
            db_path=self._db_path,
            shared_duckdb_connection=False,
        )

    def _default_wait(self, seconds: float) -> bool:
        # Sleeping on the stop event makes the wait interruptible by stop().
        return self._stop_event.wait(seconds)

    def _run(self) -> None:
        """Tick once per interval until stopped.

        The first tick is immediate: someone who just enabled auto-sync should
        not have to wait an interval for the first sync.
        """
        try:
            while not self._stop_event.is_set():
                try:
                    self._tick_once()
                except Exception:
                    # A scheduled failure must never take the worker down with
                    # it; the next interval gets another chance.
                    logger.exception("LeetCode automatic sync tick failed unexpectedly")
                if self._stop_event.is_set():
                    break
                self._wait(self._interval_seconds)
        finally:
            logger.info("LeetCode automatic sync worker stopped")

    def _tick_once(self) -> Optional[SyncStatus]:
        """One scheduled sync attempt, skipping when there is nothing to do.

        Returns the sync result when a sync actually ran, or ``None`` when it
        was skipped (disabled, no account, or a sync already in progress).
        """
        if not self._enabled:
            return None
        if not self._account_service.is_connected(PROVIDER):
            # No account means no sync and no network call at all — this is what
            # makes a disconnect stop the scheduled traffic.
            logger.debug("LeetCode auto-sync skipped: no connected account")
            return None
        if not self._sync_lock.acquire(blocking=False):
            # A manual sync (or an earlier, still-running tick) holds the lock;
            # queueing behind it would only delay the next interval's attempt.
            logger.info("LeetCode auto-sync skipped: another sync is already running")
            return None
        try:
            return self._sync_locked(limit=None, source="scheduled")
        finally:
            self._sync_lock.release()

    def _sync_locked(self, *, limit: Optional[int], source: str) -> SyncStatus:
        """Run the canonical sync while the caller holds ``_sync_lock``.

        The lock is what guarantees no overlap; this method is only responsible
        for running exactly one ``service.leetcode.sync()`` and for recording
        the outcome. It adds no retry, no backoff and no timeout of its own —
        the transport layer already owns all of that.
        """
        service = self._service_for_sync()
        started_at = datetime.now(timezone.utc)
        self._last_run_at = started_at
        try:
            result = service.leetcode.sync(limit=limit)
        except Exception as exc:
            # Already typed and scrubbed by the service surface; scrub again so
            # an exception type we did not anticipate cannot leak either.
            message = safe_error_message(exc)
            self._last_error = message
            logger.warning("LeetCode %s sync failed: %s", source, message)
            raise
        # Success, Partial and Failed are all ordinary return values here, so
        # the lock held by the caller is released in every one of them.
        self._last_error = None
        logger.info(
            "LeetCode %s sync finished: %s (%s)",
            source,
            getattr(result, "status", "unknown"),
            getattr(result, "records_added", 0),
        )
        return result

    def _service_for_sync(self) -> Any:
        """Build the dedicated sync service on first use."""
        if self._service is None:
            self._service = self._service_factory()
        return self._service

    def _close_service(self) -> None:
        """Release the dedicated service, if one was ever built."""
        service = self._service
        if service is None:
            return
        self._service = None
        try:
            service.close_storage()
        except Exception as exc:  # teardown must never block a restart
            logger.warning("Failed to close the LeetCode auto-sync service: %s", exc)

    # ───────────────────────────────────────────────────────────────────────
    # Persistence
    # ───────────────────────────────────────────────────────────────────────

    def _load_config(self) -> AutosyncConfig:
        """Read the persisted preferences, falling back to *disabled*.

        A missing file (never configured), an unreadable one (permissions, or a
        data directory deleted out from under us) and a corrupt one (a truncated
        write) all resolve to the safe default rather than raising.
        """
        try:
            raw_text = self._config_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return AutosyncConfig(enabled=False, interval_seconds=DEFAULT_INTERVAL_SECONDS)
        except OSError as exc:
            logger.warning("Ignoring unreadable LeetCode auto-sync config at %s: %s", self._config_path, exc)
            return AutosyncConfig(enabled=False, interval_seconds=DEFAULT_INTERVAL_SECONDS)

        try:
            raw = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            logger.warning("Ignoring corrupt LeetCode auto-sync config at %s: %s", self._config_path, exc)
            return AutosyncConfig(enabled=False, interval_seconds=DEFAULT_INTERVAL_SECONDS)

        if not isinstance(raw, dict):
            return AutosyncConfig(enabled=False, interval_seconds=DEFAULT_INTERVAL_SECONDS)
        return AutosyncConfig(
            enabled=bool(raw.get("enabled", False)),
            interval_seconds=_clamp_interval(raw.get("interval_seconds")),
        )

    def _save_config(self) -> None:
        """Persist the preferences atomically.

        Written via a temporary file and ``os.replace`` so a crash mid-write can
        never leave a half-written config behind — the reader tolerates one, but
        the user should not have to re-enable auto-sync because of it.
        """
        payload = {"enabled": self._enabled, "interval_seconds": self._interval_seconds}
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp_name = tempfile.mkstemp(dir=self._config_path.parent, prefix=".autosync-", suffix=".json")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(payload, handle, indent=2)
                os.replace(tmp_name, self._config_path)
            except Exception:
                # mkstemp's file lingers only if the replace never happened.
                try:
                    os.unlink(tmp_name)
                except OSError:
                    pass
                raise
        except OSError as exc:
            logger.warning("Could not persist LeetCode auto-sync config at %s: %s", self._config_path, exc)
