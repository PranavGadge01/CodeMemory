"""Unit tests for problem history reconstruction."""

from pathlib import Path
import pytest

from codememory.core.service import CodeMemoryService
from codememory.domain.enums import DifficultyLevel, SubmissionStatus


def test_history_reconstruction(tmp_path: Path):
    service = CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "data" / "test.duckdb",
    )

    prob = service.add_problem(
        title="Find Peak Element",
        difficulty=DifficultyLevel.MEDIUM,
    )

    # Attempt 1: Linear scan
    service.add_submission(
        problem_identifier=prob.slug,
        code="def findPeakElement(nums): return 0",
        language="python",
        status=SubmissionStatus.WRONG_ANSWER,
        runtime_ms=None,
        reasoning="Naive return zero index",
    )

    # Attempt 2: Binary Search
    service.add_submission(
        problem_identifier=prob.slug,
        code="def findPeakElement(nums): return nums.index(max(nums))",
        language="python",
        status=SubmissionStatus.ACCEPTED,
        runtime_ms=48.0,
        memory_mb=16.0,
        reasoning="Use max built-in",
    )

    hist = service.get_problem_history(prob.slug)
    assert hist["problem_id"] == prob.id
    assert hist["total_attempts"] >= 1
    assert hist["total_submissions"] == 2
    assert hist["accepted_submissions"] == 1
    assert hist["best_runtime_ms"] == 48.0
    assert len(hist["timeline"]) == 2
    assert hist["timeline"][0]["status"] == "Wrong Answer"
    assert hist["timeline"][1]["status"] == "Accepted"
