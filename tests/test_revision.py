"""Unit tests for RevisionService scoring and queue management."""

from pathlib import Path
import pytest

from codememory.core.service import CodeMemoryService
from codememory.domain.enums import DifficultyLevel, SubmissionStatus
from codememory.revision.revision_models import RevisionWeights
from codememory.revision.revision_service import RevisionService


def test_revision_scoring_and_queue(tmp_path: Path):
    service = CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "data" / "test.duckdb",
    )

    # 1. Easy Solved Problem
    service.add_problem(title="Easy Solved", difficulty=DifficultyLevel.EASY)
    service.add_submission(problem_identifier="easy-solved", code="pass", status=SubmissionStatus.ACCEPTED)

    # 2. Hard Unsolved Problem with multiple failures
    service.add_problem(title="Hard Struggle", difficulty=DifficultyLevel.HARD, topics=["Dynamic Programming"])
    service.add_submission(problem_identifier="hard-struggle", code="fail 1", status=SubmissionStatus.WRONG_ANSWER)
    service.add_submission(problem_identifier="hard-struggle", code="fail 2", status=SubmissionStatus.TIME_LIMIT_EXCEEDED)

    revision = RevisionService(storage=service.storage, analytics_service=service.analytics_service)

    # Priority breakdown
    bd_hard = revision.get_problem_priority("hard-struggle")
    bd_easy = revision.get_problem_priority("easy-solved")

    assert bd_hard.final_score > bd_easy.final_score
    assert bd_hard.difficulty_score == 3.0  # Hard
    assert bd_hard.failure_score >= 2.0

    # Queue ordering
    queue = revision.get_revision_queue(limit=5)
    assert len(queue) == 2
    assert queue[0].slug == "hard-struggle"

    # Mark reviewed
    service.mark_reviewed("hard-struggle", notes="Reviewed DP state transitions")
    prob = service.get_problem("hard-struggle")
    assert len(prob.notes) >= 1
