"""Unit tests for UI-independent Streamlit components and service caching."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import codememory.app.components as components
from codememory.app.components import get_service
from codememory.core.service import CodeMemoryService


@pytest.fixture(autouse=True)
def clean_service_cache():
    """Keep the process-global service caches from leaking between tests.

    ``_global_service_instance`` and the Streamlit resource cache both outlive a
    test, and a service left in them points at a directory the next test did not
    create. Clearing them on the way in as well as on the way out is what makes
    the order of these tests irrelevant.
    """
    components._global_service_instance = None
    _clear_cached_service()
    yield
    components._global_service_instance = None
    _clear_cached_service()


def _clear_cached_service() -> None:
    try:
        components._cached_service.clear()
    except Exception:
        # Outside a Streamlit runtime there may be no resource cache to clear.
        pass


def test_app_service_caching(tmp_path):
    test_db = tmp_path / "test.duckdb"
    test_data = tmp_path / "data"
    test_kb = tmp_path / "knowledge"

    service1 = CodeMemoryService(base_dir=test_data, knowledge_dir=test_kb, db_path=test_db)
    try:
        components._global_service_instance = service1

        service_a = get_service()
        service_b = get_service()
        assert service_a is service_b
        assert service_a is service1
    finally:
        # Release the DuckDB handle this instance registered process-wide by
        # database path, so it cannot be handed to a later service built against
        # a recycled path in another sandbox.
        service1.close_storage()


def test_streamlit_app_startup(tmp_path, monkeypatch):
    """Smoke test: the real Streamlit entrypoint renders without error.

    Uses Streamlit's own ``AppTest`` runner (no browser, no network) against the
    shipped ``app.py``, so a broken import or a page-level crash cannot pass CI.

    The app builds its own service here rather than inheriting one a previous
    test may have left in the module-level cache: the sandbox below is what its
    storage must live inside.
    """
    import codememory.app.app as app_module

    assert components._global_service_instance is None, (
        "a leaked cached service would point at another test's directory"
    )

    monkeypatch.chdir(tmp_path)  # keep the service's data dirs inside the sandbox
    at = AppTest.from_file(Path(app_module.__file__)).run()

    assert at.exception == [], "the Streamlit app must start and render its first page"
    # The sidebar LeetCode indicator is rendered from the service status surface.
    assert any("LC:" in (m.value or "") for m in at.markdown)

    # The app really did build inside the sandbox, and left no cached instance
    # behind for the next test to trip over.
    assert (tmp_path / "data" / "codememory.duckdb").is_file()
    assert components._global_service_instance is None
