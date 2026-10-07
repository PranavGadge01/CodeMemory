"""Performance/regression tests for the DuckDB repository's history expansion.

These tests lock in the change from the old N+1 expansion (one attempts query
per problem, one submissions query per attempt) to a constant number of bulk
queries, while proving the returned domain graph is unchanged.
"""

from pathlib import Path

from codememory.domain.enums import DifficultyLevel, SubmissionStatus
from codememory.domain.models import Attempt, Problem, Submission
from codememory.storage.duckdb_repository import DuckDBStorage


class _CountingConnection:
    """Thin proxy that records the SQL statements executed through it."""

    def __init__(self, conn):
        self._conn = conn
        self.statements: list[str] = []

    def execute(self, sql, params=None):
        self.statements.append(sql)
        if params is None:
            return self._conn.execute(sql)
        return self._conn.execute(sql, params)

    def __getattr__(self, name):
        return getattr(self._conn, name)


def _save_problem(repo, title, *, attempts=1, submissions_per_attempt=1, difficulty=DifficultyLevel.EASY):
    prob = Problem(title=title, difficulty=difficulty, topics=["Array"])
    built = []
    for n in range(1, attempts + 1):
        subs = [
            Submission(
                problem_id=prob.id,
                code=f"code-{title}-{n}-{i}",
                language="python",
                status=SubmissionStatus.ACCEPTED,
                runtime_ms=float(10 * i),
            )
            for i in range(1, submissions_per_attempt + 1)
        ]
        built.append(
            Attempt(problem_id=prob.id, attempt_number=n, status=SubmissionStatus.ACCEPTED, submissions=subs)
        )
    prob.attempts = built
    repo.save(prob)
    return prob


def test_list_all_query_count_is_constant(tmp_path: Path):
    repo = DuckDBStorage(db_path=tmp_path / "q.duckdb")
    for i in range(3):
        _save_problem(repo, f"Problem {i}", attempts=2, submissions_per_attempt=2)

    original = repo.conn
    counter = _CountingConnection(original)
    repo.conn = counter
    try:
        counter.statements.clear()
        repo.list_all()
        small_count = len(counter.statements)

        for i in range(3, 12):
            _save_problem(repo, f"Problem {i}", attempts=2, submissions_per_attempt=2)

        counter.statements.clear()
        repo.list_all()
        large_count = len(counter.statements)
    finally:
        repo.conn = original

    # 1 problems + 1 attempts + 1 submissions + 1 notes = 4 statements,
    # regardless of problem count (was 1 + N*(1 + attempts) before).
    assert small_count == 4
    assert large_count == 4
    repo.close()


def test_list_all_preserves_graph_ordering_and_empty_children(tmp_path: Path):
    repo = DuckDBStorage(db_path=tmp_path / "g.duckdb")

    _save_problem(repo, "Zebra", attempts=3, submissions_per_attempt=2)
    repo.save(Problem(title="Alpha", difficulty=DifficultyLevel.HARD, topics=["Graph"]))  # zero attempts
    _save_problem(repo, "Mango", attempts=1, submissions_per_attempt=3)

    problems = list(repo.list_all())
    assert [p.title for p in problems] == ["Alpha", "Mango", "Zebra"]

    alpha, mango, zebra = problems
    assert alpha.attempts == []
    assert [a.attempt_number for a in zebra.attempts] == [1, 2, 3]
    assert all(len(a.submissions) == 2 for a in zebra.attempts)

    # Submissions within an attempt are ordered by submitted_at ascending.
    for attempt in mango.attempts:
        times = [s.submitted_at for s in attempt.submissions]
        assert times == sorted(times)
    repo.close()


def test_list_all_handles_zero_submission_attempts(tmp_path: Path):
    repo = DuckDBStorage(db_path=tmp_path / "z.duckdb")

    prob = Problem(title="Lonely", difficulty=DifficultyLevel.MEDIUM, topics=["Array"])
    prob.attempts = [
        Attempt(problem_id=prob.id, attempt_number=1, status=SubmissionStatus.WRONG_ANSWER, submissions=[]),
        Attempt(problem_id=prob.id, attempt_number=2, status=SubmissionStatus.ACCEPTED, submissions=[]),
    ]
    repo.save(prob)
    repo.save(Problem(title="Empty", difficulty=DifficultyLevel.EASY))

    by_title = {p.title: p for p in repo.list_all()}
    assert len(by_title["Lonely"].attempts) == 2
    assert all(a.submissions == [] for a in by_title["Lonely"].attempts)
    assert by_title["Empty"].attempts == []
    repo.close()


def test_list_all_matches_per_problem_lookup(tmp_path: Path):
    repo = DuckDBStorage(db_path=tmp_path / "e.duckdb")
    for i in range(4):
        _save_problem(repo, f"Problem {i}", attempts=2, submissions_per_attempt=2)

    expanded = repo.list_all()
    for problem in expanded:
        via_id = repo.get_by_id(problem.id)
        via_slug = repo.get_by_slug(problem.slug)
        assert via_id is not None and via_slug is not None
        assert via_id.model_dump() == problem.model_dump()
        assert via_slug.model_dump() == problem.model_dump()
    repo.close()


def test_child_lookup_indexes_exist(tmp_path: Path):
    repo = DuckDBStorage(db_path=tmp_path / "i.duckdb")
    names = {row[0] for row in repo.conn.execute("SELECT index_name FROM duckdb_indexes()").fetchall()}
    assert {
        "idx_attempts_problem_id",
        "idx_submissions_attempt_id",
        "idx_submissions_problem_id",
        "idx_notes_problem_id",
    } <= names
    repo.close()