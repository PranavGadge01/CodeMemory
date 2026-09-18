"""Tests for solution evolution service."""

from codememory.ai.evolution_service import EvolutionService
from codememory.domain.enums import DifficultyLevel, SubmissionStatus
from codememory.domain.models import Problem, Submission


def test_solution_evolution_summary():
    service = EvolutionService()
    problem = Problem(title="Two Sum", slug="two-sum", difficulty=DifficultyLevel.EASY, topics=["Array", "Hash Table"])

    sub1 = Submission(
        problem_id=problem.id,
        code="for i in range(n): for j in range(i+1, n): pass",
        status=SubmissionStatus.TIME_LIMIT_EXCEEDED,
    )
    sub2 = Submission(
        problem_id=problem.id,
        code="seen = {}; seen[num] = i",
        status=SubmissionStatus.ACCEPTED,
        runtime_ms=45.0,
    )

    evo = service.generate_evolution(problem, [sub1, sub2])
    assert evo.total_attempts == 2
    assert len(evo.steps) == 2
    assert "evolved" in evo.evolution_narrative.lower()
    assert evo.key_breakthrough is not None
