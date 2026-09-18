"""Unit tests for Phase 3 PatternAnalyzer."""

from pathlib import Path
import pytest

from codememory.analytics.pattern_analyzer import PatternAnalyzer
from codememory.core.service import CodeMemoryService
from codememory.domain.enums import DifficultyLevel, SubmissionStatus


def test_pattern_detection(tmp_path: Path):
    service = CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "data" / "test.duckdb",
    )

    # Add problem with TLE and WA attempts (Brute Force -> Solved)
    prob = service.add_problem(title="N-Queens", difficulty=DifficultyLevel.HARD, topics=["Backtracking", "Recursion"])
    service.add_submission(
        problem_identifier=prob.slug,
        code="bad attempt 1",
        status=SubmissionStatus.TIME_LIMIT_EXCEEDED,
    )
    service.add_submission(
        problem_identifier=prob.slug,
        code="bad attempt 2",
        status=SubmissionStatus.TIME_LIMIT_EXCEEDED,
    )
    service.add_submission(
        problem_identifier=prob.slug,
        code="good attempt 3",
        status=SubmissionStatus.ACCEPTED,
    )

    analyzer = PatternAnalyzer(analytics_service=service.analytics_service)
    result = analyzer.analyze(unpracticed_days_threshold=0)

    assert "N-Queens" in result.repeated_tle_problems
    assert "N-Queens" in result.brute_force_before_optimized_problems
    assert len(result.high_attempt_problems) == 1
    assert result.high_attempt_problems[0]["title"] == "N-Queens"
