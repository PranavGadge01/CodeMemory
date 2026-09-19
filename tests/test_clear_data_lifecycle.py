"""Regression tests for the "Clear All Data" application lifecycle.

The Settings Danger Zone deletes the whole storage tree (``data/`` and
``knowledge/``) while a ``CodeMemoryService`` is still cached in the process.
That instance's DuckDB handle then points at a database file that no longer
exists, and — because ``DuckDBStorage`` registers its connections process-wide
by database path — simply building another service against the same path would
inherit the same dead handle. Reads would return rows that are gone from disk
and writes would vanish.

The contract these tests pin down: after the data tree is cleared and the
cached service is retired, the next application operation must run against a
freshly initialized, on-disk storage state.
"""

import shutil
import threading
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import codememory.app.components as components
from codememory.app.pages import settings_view
from codememory.connectors.leetcode.scheduler import _THREAD_NAME
from codememory.core.service import CodeMemoryService
from codememory.storage.duckdb_repository import _shared_duckdb_connections

PAGE_RUNNER = "from codememory.app.pages import settings_view\nsettings_view.render_settings_page()\n"


@pytest.fixture
def isolated_service_cache(monkeypatch, tmp_path):
    """Run inside a scratch data tree with a known-clean service cache.

    Both caches are process-global (the Streamlit resource cache and the
    module-level fallback), so a test that retires a service must not leave a
    stale instance behind for the rest of the suite — nor inherit one. The
    DuckDB connection registry is global too and keyed by the raw path string,
    so a relative ``data/codememory.duckdb`` would otherwise resolve against
    whichever directory a previous test happened to chdir into.
    """
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
    try:
        components._cached_service.clear()
    except Exception:
        pass


def _clear_data_tree_like_settings() -> None:
    """The Danger Zone deletion verbatim: remove the trees, rebuild the top level.

    Retirement of the cached service happens *before* this in the page (see
    ``test_clear_all_data_stops_the_worker_before_deleting_the_tree``); this
    helper is just the deletion, so a test can drive it on its own.
    """
    for d in ["data", "knowledge"]:
        p = Path(d)
        if p.exists():
            shutil.rmtree(p)
        p.mkdir(parents=True, exist_ok=True)


def _run_settings_page(isolated_service_cache: Path):
    """Run the real Settings page under Streamlit's AppTest (no server, no browser)."""
    from streamlit.testing.v1 import AppTest

    runner = isolated_service_cache / "run_settings_page.py"
    runner.write_text(PAGE_RUNNER, encoding="utf-8")
    app = AppTest.from_file(str(runner))
    app.run()
    assert app.exception == []
    # The destructive button is only rendered once the checkbox is accepted.
    app.checkbox("confirm_clear").check().run()
    assert any(b.key == "btn_clear_all" for b in app.button)
    return app


def _accept_clear_all(app) -> None:
    app.button("btn_clear_all").click().run()


def _page_text(app) -> str:
    return " ".join(
        getattr(element, "value", str(element))
        for kind in ("markdown", "success", "warning", "error", "info", "caption")
        for element in (getattr(app, kind, None) or [])
    )


# ─────────────────────────────────────────────────────────────────────────────
# The cached application service must be retired, not reused
# ─────────────────────────────────────────────────────────────────────────────


def test_service_after_clear_uses_fresh_on_disk_storage(isolated_service_cache):
    """After clearing, the next service sees empty storage that actually persists."""
    service = components.get_service()
    service.add_problem(title="Two Sum", difficulty="Easy")
    old_connection = service.storage.duckdb_repo.conn
    assert len(service.list_problems()) == 1

    # Retired before the delete, exactly as the Danger Zone does it: the cached
    # service's DuckDB handle must not still be open when its file disappears.
    components.reset_service()
    _clear_data_tree_like_settings()

    fresh = components.get_service()

    assert fresh is not service, "the cached service instance must be retired"
    # Not reading through the handle to the deleted database.
    assert fresh.storage.duckdb_repo.conn is not old_connection
    assert _shared_duckdb_connections.get("data/codememory.duckdb") is not old_connection
    # A real, freshly initialized database file exists on disk.
    assert Path("data/codememory.duckdb").is_file()

    assert len(fresh.list_problems()) == 0, "cleared storage must read back empty"

    # Writes through the new service land on disk and survive another rebuild.
    fresh.add_problem(title="Reverse Linked List", difficulty="Easy")
    components.reset_service()
    assert len(components.get_service().list_problems()) == 1


def test_duckdb_connection_is_shared_process_wide(isolated_service_cache):
    """Why ``reset_service`` must close storage, not merely drop the caches.

    ``DuckDBStorage`` registers its connection by database path for the whole
    process, so clearing the service caches alone leaves the handle behind for
    the next instance. This is the premise the retirement relies on — if it ever
    stops holding, ``reset_service`` is doing more work than the storage layer
    needs and this test should be retired with it.
    """
    service = components.get_service()
    connection = service.storage.duckdb_repo.conn

    components._global_service_instance = None
    try:
        components._cached_service.clear()
    except Exception:
        pass

    reused = components.get_service()
    assert reused.storage.duckdb_repo.conn is connection


def test_reset_service_outside_streamlit_runtime(isolated_service_cache):
    """``reset_service`` works without a Streamlit runtime (the fallback cache)."""
    service = components.get_service()
    assert components.get_service() is service

    components.reset_service()

    assert components._global_service_instance is None
    assert components.get_service() is not service


# ─────────────────────────────────────────────────────────────────────────────
# close_storage — the storage lifecycle the retirement relies on
# ─────────────────────────────────────────────────────────────────────────────


def test_close_storage_releases_the_duckdb_handle(tmp_path):
    """Closing unregisters the handle so a later instance reopens the database."""
    db_path = tmp_path / "data" / "codememory.duckdb"
    service = CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=db_path,
    )
    service.add_problem(title="Two Sum", difficulty="Easy")
    connection = service.storage.duckdb_repo.conn
    assert _shared_duckdb_connections[str(db_path)] is connection

    service.close_storage()

    # The handle is gone from the process-wide registry.
    assert _shared_duckdb_connections.get(str(db_path)) is None

    reopened = CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=db_path,
    )
    # Reopened a fresh connection and the persisted data is intact.
    assert reopened.storage.duckdb_repo.conn is not connection
    assert _shared_duckdb_connections[str(db_path)] is reopened.storage.duckdb_repo.conn
    assert len(reopened.list_problems()) == 1


def test_close_storage_is_safe_on_an_already_released_service(tmp_path):
    """Retiring twice must not raise and must not disturb a reopened database."""
    db_path = tmp_path / "data" / "codememory.duckdb"
    service = CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=db_path,
    )

    service.close_storage()
    service.close_storage()  # no-op, no exception

    reopened = CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=db_path,
    )
    assert reopened.list_problems() == []


def test_close_storage_leaves_persisted_data_reachable(tmp_path):
    """Retiring one service cannot take persisted data with it.

    ``DuckDBStorage`` hands the same connection to every live instance built
    against a path, so ``close_storage`` is only ever called in the app on the
    single cached service that owns the handle. What must hold regardless is
    that the data already written to disk stays reachable afterwards.
    """
    db_path = tmp_path / "data" / "codememory.duckdb"
    kwargs = {
        "base_dir": tmp_path / "data",
        "knowledge_dir": tmp_path / "knowledge",
        "db_path": db_path,
    }
    first = CodeMemoryService(**kwargs)
    first.add_problem(title="Two Sum", difficulty="Easy")
    first.close_storage()

    reopened = CodeMemoryService(**kwargs)
    assert len(reopened.list_problems()) == 1
    reopened.add_problem(title="Three Sum", difficulty="Medium")
    reopened.close_storage()

    assert len(CodeMemoryService(**kwargs).list_problems()) == 2


# ─────────────────────────────────────────────────────────────────────────────
# The real Settings page, driven end to end
# ─────────────────────────────────────────────────────────────────────────────


def test_settings_clear_all_data_rebuilds_storage(isolated_service_cache):
    """Clicking Clear All Data leaves the next operation on valid fresh storage."""
    service = components.get_service()
    service.add_problem(title="Two Sum", difficulty="Easy")
    assert len(service.list_problems()) == 1
    stale_connection = service.storage.duckdb_repo.conn

    runner = isolated_service_cache / "run_settings_page.py"
    runner.write_text(PAGE_RUNNER, encoding="utf-8")

    app = AppTest.from_file(str(runner))
    app.run()
    assert app.exception == []

    # The destructive button is only rendered once the checkbox is accepted.
    app.checkbox("confirm_clear").check().run()
    assert any(b.key == "btn_clear_all" for b in app.button)
    app.button("btn_clear_all").click().run()

    assert app.exception == []
    # The handler renders its success message then reruns, so the message itself
    # is gone by here — the clear is proven by the storage state below instead.

    # The page reran after clearing and now reads a freshly built service.
    after = components.get_service()
    assert after is not service
    assert after.storage.duckdb_repo.conn is not stale_connection
    assert Path("data/codememory.duckdb").is_file()
    assert len(after.list_problems()) == 0

    # Storage is genuinely writable, not merely readable-as-empty.
    after.add_problem(title="Climbing Stairs", difficulty="Easy")
    components.reset_service()
    assert len(components.get_service().list_problems()) == 1


def test_settings_clear_all_data_requires_confirmation(isolated_service_cache):
    """The destructive action stays behind its confirmation checkbox."""
    service = components.get_service()
    service.add_problem(title="Two Sum", difficulty="Easy")

    runner = isolated_service_cache / "run_settings_page.py"
    runner.write_text(PAGE_RUNNER, encoding="utf-8")

    app = AppTest.from_file(str(runner))
    app.run()
    assert not any(b.key == "btn_clear_all" for b in app.button), (
        "the destructive action must not render before confirmation"
    )

    # Not checked: nothing was deleted, and the cached service is untouched.
    assert app.exception == []
    assert len(components.get_service().list_problems()) == 1
    assert components.get_service() is service


def test_settings_view_retires_the_service_it_was_rendered_with(isolated_service_cache):
    """The page's own service reference is invalidated too, not just the global one.

    ``render_settings_page`` resolves its service once per render; after the
    clear, a later render must not keep using that captured instance.
    """
    service = components.get_service()
    service.add_problem(title="Two Sum", difficulty="Easy")

    runner = isolated_service_cache / "run_settings_page.py"
    runner.write_text(PAGE_RUNNER, encoding="utf-8")

    app = AppTest.from_file(str(runner))
    app.run()
    captured = settings_view.get_service()
    assert captured is service

    app.checkbox("confirm_clear").check().run()
    app.button("btn_clear_all").click().run()

    assert settings_view.get_service() is not service


# ─────────────────────────────────────────────────────────────────────────────
# The race: a live autosync worker and its open handles vs. the delete
# ─────────────────────────────────────────────────────────────────────────────


def _real_service(tmp_path: Path) -> CodeMemoryService:
    return CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "data" / "codememory.duckdb",
    )


def _spy_rmtree(monkeypatch, probe) -> list[str]:
    """Wrap ``shutil.rmtree`` so a test can observe state at deletion time.

    ``probe`` is called with the path just before the real delete happens, while
    the caller's assertions still have something to measure.
    """
    calls: list[str] = []
    real_rmtree = shutil.rmtree

    def spying_rmtree(path, *args, **kwargs):
        calls.append(str(path))
        probe(path)
        return real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(shutil, "rmtree", spying_rmtree)
    return calls


def test_clear_all_data_stops_the_worker_before_deleting_the_tree(isolated_service_cache, monkeypatch):
    """B1: the autosync worker and its open handles must be gone before the delete.

    Reproduces the race without network and without sleeping: a real scheduler
    worker is left running over the tree about to be cleared, holding a live
    DuckDB connection into ``data/``. The page must retire the service — which
    stops the worker and closes that connection — *before* the tree disappears,
    or the delete races an open handle (WinError 32 on Windows) and the app is
    left reading and writing through handles to deleted files.
    """
    service = _real_service(isolated_service_cache)
    service.add_problem(title="Two Sum", difficulty="Easy")
    # The scheduler's dedicated sync service: a *separate* connection into the
    # same tree, the one a scheduled sync would be using mid-flight.
    service.autosync._service = _real_service(isolated_service_cache)
    worker_connection = service.autosync._service.storage.duckdb_repo.conn
    # The page must see this service as the live one, so its retirement reaches
    # this scheduler rather than a fresh one built for the render.
    components._global_service_instance = service
    # Enabled with no account connected: a live worker that has nothing to sync,
    # parked on its (interruptible) interval wait. The default wait is
    # ``stop_event.wait``, so ``stop()`` can end this thread deterministically.
    threads_before = {thread.ident for thread in threading.enumerate()}
    service.autosync.set_enabled(True)
    assert service.autosync.is_running is True
    assert worker_connection.execute("SELECT 1").fetchone() == (1,), "the handle under test really is live"

    at_deletion: dict[str, object] = {}

    def probe(_path) -> None:
        at_deletion.setdefault("worker_running", service.autosync.is_running)
        at_deletion.setdefault("worker_service", service.autosync._service)

    deletions = _spy_rmtree(monkeypatch, probe)

    app = _run_settings_page(isolated_service_cache)
    _accept_clear_all(app)

    assert app.exception == []
    # The data tree was deleted, and at the moment that happened no worker was
    # running and no dedicated connection was open against it.
    assert "data" in deletions
    assert at_deletion["worker_running"] is False, "the worker must be stopped before the tree is deleted"
    assert at_deletion["worker_service"] is None, "the worker's dedicated service must be closed first"

    # The tree really is gone and rebuilt, and the app is usable over the new one.
    assert not Path("data").is_dir() or Path("data/codememory.duckdb").is_file()
    after = components.get_service()
    assert after is not service
    assert len(after.list_problems()) == 0

    # Nothing this test started is still running: the clear retired the worker,
    # and the post-clear render must not quietly restart one over the new tree.
    leftover = [
        thread
        for thread in threading.enumerate()
        if thread.ident not in threads_before and thread.is_alive() and thread.name == _THREAD_NAME
    ]
    assert leftover == [], "clearing all data must not leave an autosync worker running"


def test_clear_all_data_retries_a_transient_lock(isolated_service_cache, monkeypatch):
    """A delete that races a handle being released is retried, not half-finished.

    The storage tree ends up fully cleared and the app keeps working; the user is
    never told "all data cleared" over a partially deleted tree.
    """
    service = components.get_service()
    service.add_problem(title="Two Sum", difficulty="Easy")

    data_tree = str(Path("data"))
    attempts: list[str] = []

    def flaky_rmtree(path, *args, **kwargs):
        attempts.append(str(path))
        # The first attempt on the data tree loses to a handle still being let
        # go of — the transient lock the retry exists for.
        if str(path) == data_tree and attempts.count(data_tree) == 1:
            raise PermissionError(32, "The process cannot access the file")
        return real_rmtree(path, *args, **kwargs)

    real_rmtree = shutil.rmtree
    monkeypatch.setattr(shutil, "rmtree", flaky_rmtree)

    app = _run_settings_page(isolated_service_cache)
    _accept_clear_all(app)

    assert app.exception == []
    assert attempts.count(data_tree) == 2, "one transient failure is retried, then the delete completes"
    assert Path("data").is_dir()
    assert len(components.get_service().list_problems()) == 0, "the clear completed, not just started"


def test_clear_all_data_reports_failure_and_keeps_data_intact(isolated_service_cache, monkeypatch):
    """An unfixable lock is reported honestly; no success over a torn tree.

    The service is still retired first, so the app keeps running against the
    surviving storage instead of through handles to files that no longer exist.
    """
    service = components.get_service()
    service.add_problem(title="Two Sum", difficulty="Easy")
    stale_connection = service.storage.duckdb_repo.conn

    def locked_rmtree(path, *args, **kwargs):
        raise PermissionError(32, "The process cannot access the file")

    monkeypatch.setattr(shutil, "rmtree", locked_rmtree)

    app = _run_settings_page(isolated_service_cache)
    _accept_clear_all(app)

    assert app.exception == [], "a failed clear is reported, never raised as a traceback"
    assert "could not be deleted" in _page_text(app)

    # Nothing was claimed as cleared, and nothing was lost.
    assert Path("data/codememory.duckdb").is_file()
    after = components.get_service()
    assert after is not service, "the live service was still retired, so nothing reads through a stale handle"
    assert after.storage.duckdb_repo.conn is not stale_connection
    assert len(after.list_problems()) == 1, "the surviving data is still reachable"
