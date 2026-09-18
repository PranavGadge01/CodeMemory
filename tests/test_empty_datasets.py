"""Edge case and empty dataset robustness tests."""

from pathlib import Path
import pytest

from codememory.core.service import CodeMemoryService


def test_empty_dataset_handling(tmp_path: Path):
    service = CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "data" / "empty.duckdb",
    )

    # 1. Analytics on empty DB
    overview = service.analytics_service.get_overview()
    assert overview.total_problems == 0
    assert overview.accepted_problems == 0
    assert overview.avg_solving_time_minutes is None

    topic_stats = service.analytics_service.get_topic_statistics()
    assert topic_stats == []

    diff_stats = service.analytics_service.get_difficulty_statistics()
    assert diff_stats == []

    lang_stats = service.analytics_service.get_language_statistics()
    assert lang_stats == []

    # 2. Search on empty DB
    search_res = service.search(query="nonexistent")
    assert search_res == []

    # 3. Revision on empty DB
    rev_queue = service.get_revision_queue()
    assert rev_queue == []

    due_queue = service.get_due_problems()
    assert due_queue == []

    # 4. Pattern analysis on empty DB
    patterns = service.analyze_patterns()
    assert patterns.weak_topics == []
    assert patterns.repeated_tle_problems == []

    # 5. Insights on empty DB
    insights = service.generate_insights()
    assert len(insights) == 1
