"""Unit tests for composite multi-tier persistence."""

from pathlib import Path
import pytest

from codememory.domain.enums import DifficultyLevel, SubmissionStatus
from codememory.domain.models import Attempt, Problem, Submission
from codememory.storage.composite_repository import CompositeStorage


def test_composite_storage_atomic_sync(tmp_path: Path):
    storage = CompositeStorage(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "data" / "codememory.duckdb",
    )

    prob = Problem(
        title="Word Search",
        difficulty=DifficultyLevel.MEDIUM,
        topics=["Backtracking", "Matrix"],
    )
    sub = Submission(
        problem_id=prob.id,
        code="def exist(board, word): pass",
        language="python",
        status=SubmissionStatus.ACCEPTED,
    )
    att = Attempt(problem_id=prob.id, attempt_number=1, status=SubmissionStatus.ACCEPTED, submissions=[sub])
    prob.attempts = [att]

    storage.save(prob)

    # 1. DuckDB Check
    from_db = storage.duckdb_repo.get_by_slug("word-search")
    assert from_db is not None
    assert from_db.title == "Word Search"

    # 2. Filesystem Check
    from_fs = storage.fs_repo.get_by_slug("word-search")
    assert from_fs is not None
    assert (tmp_path / "knowledge" / "word-search" / "problem.md").exists()

    # 3. Parquet Check
    from_pq = storage.parquet_repo.get_by_slug("word-search")
    assert from_pq is not None
    assert from_pq.title == "Word Search"
