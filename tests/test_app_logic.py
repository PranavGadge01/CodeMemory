"""Unit tests for UI-independent Streamlit components and service caching."""

from pathlib import Path

from codememory.app.components import get_service, _global_service_instance
from codememory.core.service import CodeMemoryService


def test_app_service_caching(tmp_path):
    test_db = tmp_path / "test.duckdb"
    test_data = tmp_path / "data"
    test_kb = tmp_path / "knowledge"

    service1 = CodeMemoryService(base_dir=test_data, knowledge_dir=test_kb, db_path=test_db)
    import codememory.app.components as comps
    comps._global_service_instance = service1

    service_a = get_service()
    service_b = get_service()
    assert service_a is service_b
    assert service_a is service1


def test_streamlit_app_startup(tmp_path, monkeypatch):
    """Smoke test: the real Streamlit entrypoint renders without error.

    Uses Streamlit's own ``AppTest`` runner (no browser, no network) against the
    shipped ``app.py``, so a broken import or a page-level crash cannot pass CI.
    """
    from streamlit.testing.v1 import AppTest

    import codememory.app.app as app_module

    monkeypatch.chdir(tmp_path)  # keep the service's data dirs inside the sandbox
    at = AppTest.from_file(Path(app_module.__file__)).run()

    assert at.exception == [], "the Streamlit app must start and render its first page"
    # The sidebar LeetCode indicator is rendered from the service status surface.
    assert any("LC:" in (m.value or "") for m in at.markdown)

