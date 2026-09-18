"""Unit tests for CodeMemoryService API operations."""

from pathlib import Path
import pytest

from codememory.core.service import CodeMemoryService
from codememory.domain.enums import DifficultyLevel, SubmissionStatus
from codememory.domain.exceptions import ProblemNotFoundError


def test_service_crud_flow(tmp_path: Path):
    service = CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "data" / "codememory.duckdb",
    )

    # 1. Add problem
    prob = service.add_problem(
        title="Container With Most Water",
        difficulty=DifficultyLevel.MEDIUM,
        topics=["Array", "Two Pointers"],
    )
    assert prob.slug == "container-with-most-water"

    # 2. Add attempt and submission
    service.add_submission(
        problem_identifier=prob.slug,
        code="def maxArea(height):\n    pass",
        language="python",
        status=SubmissionStatus.ACCEPTED,
        runtime_ms=55.0,
        memory_mb=27.0,
        reasoning="Two pointer approach moving inner lower wall",
    )

    # 3. Retrieve problem
    fetched = service.get_problem("container-with-most-water")
    assert fetched is not None
    assert len(fetched.attempts) == 1
    assert fetched.latest_accepted_submission.runtime_ms == 55.0

    # 4. Error case
    with pytest.raises(ProblemNotFoundError):
        service.get_problem("non-existent-problem")
