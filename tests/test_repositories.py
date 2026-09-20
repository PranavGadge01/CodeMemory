"""Unit tests for individual storage repository layers (FS, Parquet, DuckDB)."""

from pathlib import Path
import pytest

from codememory.domain.enums import DifficultyLevel, SubmissionStatus
from codememory.domain.models import Attempt, Problem, Submission
from codememory.storage.duckdb_repository import DuckDBStorage
from codememory.storage.fs_repository import FilesystemStorage
from codememory.storage.parquet_repository import ParquetStorage


def test_filesystem_repository(tmp_path: Path):
    fs_repo = FilesystemStorage(root_dir=tmp_path / "knowledge")

    prob = Problem(
        title="Climbing Stairs",
        difficulty=DifficultyLevel.EASY,
        topics=["Dynamic Programming", "Math"],
        statement="You are climbing a staircase. It takes n steps to reach the top.",
    )
    sub = Submission(
        problem_id=prob.id,
        code="def climbStairs(n):\n    return n",
        language="python",
        status=SubmissionStatus.ACCEPTED,
        runtime_ms=30.0,
        memory_mb=14.0,
    )
    att = Attempt(
        problem_id=prob.id,
        attempt_number=1,
        approach_summary="Simple DP",
        status=SubmissionStatus.ACCEPTED,
        submissions=[sub],
    )
    prob.attempts = [att]

    fs_repo.save(prob)

    prob_dir = tmp_path / "knowledge" / "climbing-stairs"
    assert prob_dir.exists()
    assert (prob_dir / "problem.md").exists()
    assert (prob_dir / "attempts.md").exists()
    assert (prob_dir / "solution.py").exists()
    assert (prob_dir / "metadata.json").exists()

    fetched = fs_repo.get_by_slug("climbing-stairs")
    assert fetched is not None
    assert fetched.title == "Climbing Stairs"


def test_duckdb_repository(tmp_path: Path):
    db_file = tmp_path / "test.duckdb"
    db_repo = DuckDBStorage(db_path=db_file)

    prob = Problem(
        title="Coin Change",
        difficulty=DifficultyLevel.MEDIUM,
        topics=["Dynamic Programming", "BFS"],
    )
    sub = Submission(
        problem_id=prob.id,
        code="def coinChange(coins, amount): pass",
        language="python",
        status=SubmissionStatus.ACCEPTED,
        runtime_ms=80.0,
        memory_mb=16.0,
    )
    att = Attempt(problem_id=prob.id, attempt_number=1, status=SubmissionStatus.ACCEPTED, submissions=[sub])
    prob.attempts = [att]

    db_repo.save(prob)

    fetched = db_repo.get_by_slug("coin-change")
    assert fetched is not None
    assert fetched.title == "Coin Change"
    assert len(fetched.attempts) == 1
    assert fetched.attempts[0].submissions[0].runtime_ms == 80.0
    db_repo.close()


def test_duckdb_repository_concurrent_reads(tmp_path: Path):
    # The pooled DuckDB connection is shared by every storage instance in the
    # process built against the same path — including all of a threaded
    # server's request threads. One connection cannot run two statements at
    # once: interleaving them let one thread's ``SELECT * FROM problems`` rows
    # be consumed by another thread's attempt-row fetch inside
    # ``_build_problem_from_row``, so ``attempt_number`` received the slug.
    # Reads must therefore be safe to run concurrently.
    from concurrent.futures import ThreadPoolExecutor

    db_file = tmp_path / "test.duckdb"
    db_repo = DuckDBStorage(db_path=db_file)

    prob = Problem(
        title="Coin Change",
        difficulty=DifficultyLevel.MEDIUM,
        topics=["Dynamic Programming", "BFS"],
    )
    sub = Submission(
        problem_id=prob.id,
        code="def coinChange(coins, amount): pass",
        language="python",
        status=SubmissionStatus.ACCEPTED,
        runtime_ms=80.0,
        memory_mb=16.0,
    )
    att = Attempt(problem_id=prob.id, attempt_number=1, status=SubmissionStatus.ACCEPTED, submissions=[sub])
    prob.attempts = [att]
    db_repo.save(prob)

    def read_once(_):
        fetched = db_repo.get_by_slug("coin-change")
        if fetched is None:
            return None
        return (fetched.title, [a.attempt_number for a in fetched.attempts])

    try:
        with ThreadPoolExecutor(max_workers=20) as pool:
            results = list(pool.map(read_once, range(20)))
    finally:
        db_repo.close()

    assert len(results) == 20
    assert all(r == ("Coin Change", [1]) for r in results), results


def test_duckdb_repository_concurrent_read_write(tmp_path: Path):
    # A reader must not observe a half-written graph, and a writer must not
    # corrupt a concurrent reader's result set.
    from concurrent.futures import ThreadPoolExecutor

    db_file = tmp_path / "test.duckdb"
    db_repo = DuckDBStorage(db_path=db_file)

    for i in range(5):
        prob = Problem(
            title=f"Problem {i}",
            difficulty=DifficultyLevel.EASY,
            topics=["Array"],
        )
        sub = Submission(
            problem_id=prob.id,
            code=f"def p{i}(): pass",
            language="python",
            status=SubmissionStatus.ACCEPTED,
        )
        prob.attempts = [Attempt(problem_id=prob.id, attempt_number=1, status=SubmissionStatus.ACCEPTED, submissions=[sub])]
        db_repo.save(prob)

    def read_once(_):
        return {p.slug: [a.attempt_number for a in p.attempts] for p in db_repo.list_all()}

    try:
        with ThreadPoolExecutor(max_workers=12) as pool:
            readers = list(pool.map(read_once, range(12)))
            pool.submit(db_repo.get_by_slug, "problem-0").result()
    finally:
        db_repo.close()

    expected = {f"problem-{i}": [1] for i in range(5)}
    assert all(r == expected for r in readers), readers


def test_parquet_repository(tmp_path: Path):
    p_dir = tmp_path / "parquet"
    parquet_repo = ParquetStorage(data_dir=p_dir)

    prob = Problem(
        title="Merge Intervals",
        difficulty=DifficultyLevel.MEDIUM,
        topics=["Array", "Sorting"],
    )
    sub = Submission(problem_id=prob.id, code="pass", status=SubmissionStatus.ACCEPTED)
    att = Attempt(problem_id=prob.id, attempt_number=1, status=SubmissionStatus.ACCEPTED, submissions=[sub])
    prob.attempts = [att]

    parquet_repo.save(prob)

    assert (p_dir / "problems.parquet").exists()
    assert (p_dir / "attempts.parquet").exists()
    assert (p_dir / "submissions.parquet").exists()

    all_p = parquet_repo.list_all()
    assert len(all_p) == 1
    assert all_p[0].title == "Merge Intervals"
