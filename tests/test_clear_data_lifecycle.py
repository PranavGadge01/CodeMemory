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
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import codememory.app.components as components
from codememory.app.pages import settings_view
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
    """The Danger Zone action verbatim: delete, then rebuild the top level only."""
    for d in ["data", "knowledge"]:
        p = Path(d)
        if p.exists():
            shutil.rmtree(p)
        p.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# The cached application service must be retired, not reused
# ─────────────────────────────────────────────────────────────────────────────


def test_service_after_clear_uses_fresh_on_disk_storage(isolated_service_cache):
    """After clearing, the next service sees empty storage that actually persists."""
    service = components.get_service()
    service.add_problem(title="Two Sum", difficulty="Easy")
    old_connection = service.storage.duckdb_repo.conn
    assert len(service.list_problems()) == 1

    _clear_data_tree_like_settings()
    components.reset_service()

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
