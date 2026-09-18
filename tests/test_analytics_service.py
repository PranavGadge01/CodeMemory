# -*- coding: utf-8 -*-
"""Additional tests for AnalyticsService to increase coverage and verify edge cases.

This file tests:
- Empty dataset handling for all analytics methods.
- Detailed statistics calculations for overview, topics, difficulty, language, attempts, progress over time, and struggle problems.
- Correct handling of duplicate problems, multiple attempts, and various submission statuses.
"""

import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from codememory.analytics.analytics_service import AnalyticsService
from codememory.core.service import CodeMemoryService
from codememory.domain.enums import DifficultyLevel, SubmissionStatus

@pytest.fixture
def empty_service(tmp_path: Path) -> AnalyticsService:
    """Create a CodeMemoryService with no data and return its AnalyticsService."""
    service = CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "data" / "empty.duckdb",
    )
    # No problems added
    return AnalyticsService(storage=service.storage)

def test_overview_empty(empty_service: AnalyticsService):
    overview = empty_service.get_overview()
    assert overview.total_problems == 0
    assert overview.total_attempts == 0
    assert overview.total_submissions == 0
    assert overview.accepted_problems == 0
    assert overview.unsolved_problems == 0
    assert overview.overall_acceptance_rate_pct == 0.0
    assert overview.avg_attempts_per_solved_problem == 0.0
    assert overview.first_attempt_acceptance_rate_pct == 0.0
    assert overview.repeated_problem_rate_pct == 0.0
    assert overview.avg_solving_time_minutes is None

def test_topic_statistics_empty(empty_service: AnalyticsService):
    assert empty_service.get_topic_statistics() == []

def test_difficulty_statistics_empty(empty_service: AnalyticsService):
    assert empty_service.get_difficulty_statistics() == []

def test_language_statistics_empty(empty_service: AnalyticsService):
    # Should return empty list, not raise
    assert empty_service.get_language_statistics() == []

def test_attempt_statistics_empty(empty_service: AnalyticsService):
    stats = empty_service.get_attempt_statistics()
    assert stats.total_attempts == 0
    assert stats.avg_attempts_per_problem == 0.0
    assert stats.single_attempt_solved_count == 0
    assert stats.multiple_attempt_solved_count == 0
    assert stats.max_attempts_single_problem == 0
    assert stats.brute_force_to_optimized_count == 0

def test_progress_over_time_empty(empty_service: AnalyticsService):
    assert empty_service.get_progress_over_time() == []

def test_struggle_problems_empty(empty_service: AnalyticsService):
    assert empty_service.get_struggle_problems() == []

@pytest.fixture
def populated_service(tmp_path: Path) -> AnalyticsService:
    """Create a service with a variety of problems, attempts, and submissions for analytics testing."""
    svc = CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "data" / "populated.duckdb",
    )
    # Problem 1: Easy, solved in first attempt (Accepted)
    p1 = svc.add_problem(
        title="Two Sum",
        difficulty=DifficultyLevel.EASY,
        topics=["Array", "Hash Table"],
    )
    svc.add_submission(
        problem_identifier=p1.slug,
        code="solution",
        language="python",
        status=SubmissionStatus.ACCEPTED,
        runtime_ms=30.0,
        memory_mb=16.0,
    )
    # Problem 2: Medium, solved after a TLE then Accepted
    p2 = svc.add_problem(
        title="LRU Cache",
        difficulty=DifficultyLevel.MEDIUM,
        topics=["Hash Table", "Design"],
    )
    svc.add_submission(
        problem_identifier=p2.slug,
        code="slow",
        language="python",
        status=SubmissionStatus.TIME_LIMIT_EXCEEDED,
    )
    svc.add_submission(
        problem_identifier=p2.slug,
        code="optimized",
        language="python",
        status=SubmissionStatus.ACCEPTED,
        runtime_ms=70.0,
        memory_mb=20.0,
    )
    # Problem 3: Hard, unsolved with two WA attempts
    p3 = svc.add_problem(
        title="Median of Two Sorted Arrays",
        difficulty=DifficultyLevel.HARD,
        topics=["Binary Search", "Divide and Conquer"],
    )
    svc.add_submission(
        problem_identifier=p3.slug,
        code="attempt1",
        language="cpp",
        status=SubmissionStatus.WRONG_ANSWER,
    )
    svc.add_submission(
        problem_identifier=p3.slug,
        code="attempt2",
        language="cpp",
        status=SubmissionStatus.WRONG_ANSWER,
    )
    # Problem 4: Easy, solved after two attempts (first WA, second Accepted)
    p4 = svc.add_problem(
        title="Valid Parentheses",
        difficulty=DifficultyLevel.EASY,
        topics=["Stack", "String"],
    )
    svc.add_submission(
        problem_identifier=p4.slug,
        code="bad",
        language="java",
        status=SubmissionStatus.WRONG_ANSWER,
    )
    svc.add_submission(
        problem_identifier=p4.slug,
        code="good",
        language="java",
        status=SubmissionStatus.ACCEPTED,
        runtime_ms=10.0,
        memory_mb=8.0,
    )
    # Adjust timestamps for progress over time testing
    now = datetime.now(timezone.utc)
    for problem in svc.storage.list_all():
        for attempt in problem.attempts:
            for sub in attempt.submissions:
                sub.submitted_at = now - timedelta(days=1)
    return AnalyticsService(storage=svc.storage)

def test_overview_populated(populated_service: AnalyticsService):
    overview = populated_service.get_overview()
    assert overview.total_problems == 4
    assert overview.accepted_problems == 3  # p1, p2, p4 solved
    assert overview.unsolved_problems == 1
    assert overview.total_attempts == 7
    assert overview.total_submissions == 7
    assert overview.overall_acceptance_rate_pct > 0
    assert overview.avg_attempts_per_solved_problem > 0
    assert overview.first_attempt_acceptance_rate_pct > 0
    assert overview.repeated_problem_rate_pct > 0
    assert overview.avg_solving_time_minutes is not None

def test_topic_statistics_populated(populated_service: AnalyticsService):
    stats = populated_service.get_topic_statistics()
    topics = {s.topic for s in stats}
    expected = {"Array", "Hash Table", "Design", "Binary Search", "Divide and Conquer", "Stack", "String"}
    assert expected.issubset(topics)
    hash_stat = next(t for t in stats if t.topic == "Hash Table")
    assert hash_stat.total_problems == 2
    assert hash_stat.solved_problems == 2
    assert hash_stat.total_submissions >= 3
    for s in stats:
        assert 0.0 <= s.acceptance_rate_pct <= 100.0
        assert 0.0 <= s.success_rate_pct <= 100.0

def test_difficulty_statistics_populated(populated_service: AnalyticsService):
    stats = populated_service.get_difficulty_statistics()
    diff_map = {d.difficulty: d for d in stats}
    assert diff_map["Easy"].total_problems == 2
    assert diff_map["Medium"].total_problems == 1
    assert diff_map["Hard"].total_problems == 1
    assert diff_map["Easy"].solved_problems == 2
    assert diff_map["Medium"].solved_problems == 1
    assert diff_map["Hard"].solved_problems == 0

def test_language_statistics_populated(populated_service: AnalyticsService):
    stats = populated_service.get_language_statistics()
    langs = {l.language for l in stats}
    assert langs.issuperset({"python", "cpp", "java"})
    python_stat = next(l for l in stats if l.language == "python")
    assert python_stat.total_submissions == 4
    assert python_stat.accepted_submissions == 3
    assert python_stat.acceptance_rate_pct == pytest.approx(75.0)

def test_attempt_statistics_populated(populated_service: AnalyticsService):
    stats = populated_service.get_attempt_statistics()
    assert stats.total_attempts == 7
    assert stats.single_attempt_solved_count == 1
    assert stats.multiple_attempt_solved_count == 2
    assert stats.max_attempts_single_problem == 3
    assert stats.brute_force_to_optimized_count == 1

def test_progress_over_time_populated(populated_service: AnalyticsService):
    prog = populated_service.get_progress_over_time(granularity="day")
    assert len(prog) == 1
    entry = prog[0]
    assert entry.total_submissions == 7
    assert entry.accepted_submissions == 3
    assert entry.problems_solved == 3

def test_struggle_problems_populated(populated_service: AnalyticsService):
    struggles = populated_service.get_struggle_problems(limit=5)
    assert struggles[0].status == "Unsolved"
    assert struggles[0].problem_id is not None
    p3_struggle = next(s for s in struggles if s.title == "Median of Two Sorted Arrays")
    assert p3_struggle.failed_attempts == 2
    assert p3_struggle.failed_submissions == 2
    assert len(struggles) <= 5
