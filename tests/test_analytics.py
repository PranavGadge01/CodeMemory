"""Unit tests for Phase 3 Analytics metrics and AnalyticsService."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest

from codememory.analytics.analytics_service import AnalyticsService
from codememory.core.service import CodeMemoryService
from codememory.domain.enums import DifficultyLevel, SubmissionStatus


def test_analytics_metrics(tmp_path: Path):
    service = CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "data" / "test.duckdb",
    )

    # 1. Add Two Sum (Easy, Solved with 2 attempts: 1 TLE, 1 Accepted)
    ts = service.add_problem(title="Two Sum", difficulty=DifficultyLevel.EASY, topics=["Array", "Hash Table"])
    service.add_submission(
        problem_identifier=ts.slug,
        code="brute force",
        language="python",
        status=SubmissionStatus.TIME_LIMIT_EXCEEDED,
    )
    service.add_submission(
        problem_identifier=ts.slug,
        code="hash map",
        language="python",
        status=SubmissionStatus.ACCEPTED,
        runtime_ms=40.0,
        memory_mb=16.0,
    )

    # 2. Add LRU Cache (Medium, Unsolved with 2 WA attempts)
    lru = service.add_problem(title="LRU Cache", difficulty=DifficultyLevel.MEDIUM, topics=["Hash Table", "Design"])
    service.add_submission(
        problem_identifier=lru.slug,
        code="bad dict",
        language="cpp",
        status=SubmissionStatus.WRONG_ANSWER,
    )

    analytics = AnalyticsService(storage=service.storage)

    # Test Overview
    overview = analytics.get_overview()
    assert overview.total_problems == 2
    assert overview.accepted_problems == 1
    assert overview.unsolved_problems == 1
    assert overview.total_attempts >= 2
    assert overview.total_submissions == 3
    assert overview.overall_acceptance_rate_pct > 0.0

    # Test Topic Stats
    topic_stats = analytics.get_topic_statistics()
    assert len(topic_stats) >= 2
    hash_table_stat = next(t for t in topic_stats if t.topic == "Hash Table")
    assert hash_table_stat.total_problems == 2
    assert hash_table_stat.solved_problems == 1

    # Test Difficulty Stats
    diff_stats = analytics.get_difficulty_statistics()
    easy_stat = next(d for d in diff_stats if d.difficulty == "Easy")
    assert easy_stat.solved_problems == 1

    # Test Language Stats
    lang_stats = analytics.get_language_statistics()
    assert len(lang_stats) >= 1

    # Test Attempt Stats
    att_stats = analytics.get_attempt_statistics()
    assert att_stats.total_attempts >= 2

    # Test Progress Over Time
    prog = analytics.get_progress_over_time(granularity="day")
    assert len(prog) >= 1

    # Test Struggle Problems
    struggles = analytics.get_struggle_problems()
    assert len(struggles) >= 1
    assert struggles[0].problem_id == lru.id
