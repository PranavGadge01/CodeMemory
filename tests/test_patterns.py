"""Tests for My Patterns personal DSA memory service."""

from codememory.domain.enums import DifficultyLevel, SubmissionStatus
from codememory.domain.models import Problem, Submission
from codememory.patterns.my_patterns_service import MyPatternsService


def test_my_patterns_service():
    service = MyPatternsService()
    p1 = Problem(title="Two Sum", slug="two-sum", difficulty=DifficultyLevel.EASY, topics=["Array", "Hash Table"])
    s1 = Submission(problem_id=p1.id, code="def twoSum(): pass", language="python", mistakes="TLE on nested loops", reasoning="Brute force", status=SubmissionStatus.TIME_LIMIT_EXCEEDED)
    s2 = Submission(problem_id=p1.id, code="def twoSum(): seen = {}", language="python", reasoning="Hash Table", status=SubmissionStatus.ACCEPTED)

    summary = service.analyze_patterns([p1], [s1, s2])
    assert summary.avg_attempts_to_solve == 2.0
    assert "python" in summary.preferred_languages
    assert len(summary.frequent_mistakes) > 0
    assert len(summary.strengths) > 0
