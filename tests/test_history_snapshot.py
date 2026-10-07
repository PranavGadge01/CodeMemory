"""Unit tests for the shared read-only history snapshot."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from codememory.domain.enums import DifficultyLevel, SubmissionStatus
from codememory.domain.models import Attempt, Problem, Submission
from codememory.storage.history import HistorySnapshot


def _problem(title, slug, attempts=1, subs_per_attempt=1):
    problem = Problem(title=title, slug=slug, difficulty=DifficultyLevel.EASY, topics=["Array"])
    base = datetime.now(timezone.utc)
    built = []
    for n in range(1, attempts + 1):
        subs = [
            Submission(
                problem_id=problem.id,
                code="x",
                status=SubmissionStatus.ACCEPTED,
                submitted_at=base + timedelta(minutes=n * 10 + i),
            )
            for i in range(subs_per_attempt)
        ]
        built.append(Attempt(problem_id=problem.id, attempt_number=n, submissions=subs))
    problem.attempts = built
    return problem


def test_snapshot_indexes_and_lookups():
    a = _problem("Two Sum", "two-sum", attempts=2, subs_per_attempt=2)
    b = _problem("Add Two", "add-two", attempts=0)

    snap = HistorySnapshot.from_problems([a, b])

    assert snap.problems == (a, b)
    assert snap.get_problem_by_id(a.id) is a
    assert snap.get_problem_by_slug("two-sum") is a
    assert snap.resolve_problem("two-sum") is a
    assert snap.resolve_problem(a.id) is a
    assert snap.resolve_problem("missing") is None
    assert snap.attempts_for_problem(b.id) == ()
    assert len(snap.attempts_for_problem(a.id)) == 2
    assert len(snap.submissions_for_attempt(a.attempts[0].id)) == 2


def test_snapshot_submissions_are_ordered_by_time():
    problem = _problem("Ordered", "ordered", attempts=2, subs_per_attempt=2)
    snap = HistorySnapshot.from_problems([problem])

    subs = snap.submissions_for_problem(problem.id)
    times = [s.submitted_at for s in subs]
    assert times == sorted(times)
    assert len(subs) == 4


def test_snapshot_from_storage_matches_list_all(tmp_path: Path):
    from codememory.storage.duckdb_repository import DuckDBStorage

    repo = DuckDBStorage(db_path=tmp_path / "s.duckdb")
    problem = _problem("Solo", "solo")
    repo.save(problem)

    snap = HistorySnapshot.from_storage(repo)
    direct = repo.list_all()
    assert snap.problems == tuple(direct)
    assert snap.is_empty is False
    repo.close()


def test_empty_snapshot():
    snap = HistorySnapshot.from_problems([])
    assert snap.is_empty is True
    assert snap.resolve_problem("x") is None
    assert snap.submissions_for_problem("x") == []