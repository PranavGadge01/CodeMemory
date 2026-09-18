"""Unit tests for UI-independent Streamlit components and service caching."""

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
