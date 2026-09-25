"""Regression tests for the LeetCode sync → dashboard data loss.

Both failures shared one symptom — every dashboard metric read zero while the
LeetCode sync reported 20 records discovered — and two independent root causes:

1. ``CompositeStorage`` answered ``get_by_slug`` / ``get_by_id`` from the
   filesystem *export* tier when DuckDB had no such row. The sync engine dedupes
   against the problem object that lookup returns, so it matched the exported
   records, reported the whole window as ``skipped``, and never persisted
   anything into the canonical store that ``list_all`` (and therefore the
   dashboard and analytics) reads.

2. ``DuckDBStorage`` silently substituted an in-memory database when the on-disk
   file was already locked by another process. A second server pointed at the
   same file then served an empty ephemeral database forever while still
   reporting ``duckdb=ok``.
"""

from pathlib import Path
from unittest.mock import MagicMock

import duckdb
import pytest

from codememory.connectors.account.service import AccountService
from codememory.connectors.leetcode.models import LeetCodeSubmissionRaw
from codememory.connectors.leetcode.service import LeetCodeAccountService
from codememory.core.service import CodeMemoryService
from codememory.storage.composite_repository import CompositeStorage
from codememory.storage.duckdb_repository import DuckDBStorage

_PROFILE = {
    "username": "syncuser",
    "real_name": "Sync User",
    "user_avatar": "https://leetcode.com/a.png",
    "ranking": 1234,
    "solved_all": 2,
    "solved_easy": 1,
    "solved_medium": 1,
    "solved_hard": 0,
}


def _raw(submission_id: str, title: str, slug: str) -> LeetCodeSubmissionRaw:
    """A raw accepted submission, exactly as the public API shapes it."""
    return LeetCodeSubmissionRaw(
        id=submission_id,
        submission_id=submission_id,
        title=title,
        title_slug=slug,
        language="python3",
        status="Accepted",
        timestamp=1700000000,
    )


def _mock_client() -> MagicMock:
    client = MagicMock()
    client.fetch_user_profile.return_value = _PROFILE
    client.fetch_user_submissions.return_value = [
        _raw("111", "Two Sum", "two-sum"),
        _raw("112", "Add Two Numbers", "add-two-numbers"),
    ]
    client.fetch_problem_details.return_value = None
    return client


def _service(tmp_path: Path) -> CodeMemoryService:
    """A service whose storage is a real, empty canonical DuckDB store."""
    service = CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "cm.duckdb",
    )
    service._leetcode_service = LeetCodeAccountService(
        service,
        account_service=AccountService(data_dir=tmp_path / "data"),
        client=_mock_client(),
    )
    service._leetcode_service.connect("syncuser")
    return service


def test_sync_imports_into_canonical_store_despite_export_tier(tmp_path: Path):
    """The export tier must not satisfy a lookup the canonical store cannot.

    This is the failure that made the sync report ``recordsImported: 0,
    recordsSkipped: 20`` on an empty database.
    """
    service = _service(tmp_path)
    try:
        storage = service.storage

        # Reproduce the exact precondition from the live system: an exported
        # record for one of the problems about to be synced exists in the
        # filesystem tier, while the canonical DuckDB row has been removed.
        # The export still carries the external submission id, which is what the
        # dedup guard used to match on.
        from codememory.domain.enums import DifficultyLevel, SubmissionStatus
        from codememory.domain.models import Attempt, Problem, Submission

        exported = Problem(title="Two Sum", difficulty=DifficultyLevel.EASY, topics=["Array"])
        exported.attempts = [
            Attempt(
                problem_id=exported.id,
                attempt_number=1,
                status=SubmissionStatus.ACCEPTED,
                submissions=[
                    Submission(
                        id="leetcode_111",
                        problem_id=exported.id,
                        code="",
                        language="python3",
                        status=SubmissionStatus.ACCEPTED,
                        submission_id="leetcode_111",
                    )
                ],
            )
        ]
        storage.save(exported)
        # Remove only the canonical row, leaving the export intact. (Direct SQL:
        # the repository's ``delete`` also fans the Parquet tier out and its
        # rowcount contract is not the point of this test.)
        storage.duckdb_repo.conn.execute("DELETE FROM problems WHERE id = ?", [exported.id])

        # The precondition: the export answers, the canonical store does not.
        assert storage.fs_repo.get_by_slug("two-sum") is not None
        assert storage.duckdb_repo.get_by_slug("two-sum") is None

        result = service.leetcode.sync()

        assert result.status.value == "Success"
        assert result.records_discovered == 2
        assert result.records_failed == 0
        # The whole window was imported rather than deduped against the export.
        assert result.records_added == 2
        assert result.records_skipped == 0

        # And it landed where the dashboard actually reads.
        assert len(service.list_problems()) == 2
        persisted = [
            s
            for problem in service.list_problems()
            for attempt in problem.attempts
            for s in attempt.submissions
        ]
        assert {s.id for s in persisted} == {"leetcode_111", "leetcode_112"}
    finally:
        service.close_storage()


def test_sync_stays_idempotent_after_the_export_tier_is_ignored(tmp_path: Path):
    """Re-syncing the same window imports nothing the second time.

    Idempotency must hold through the fix: the guard now reads the canonical
    store, which the first sync populated.
    """
    service = _service(tmp_path)
    try:
        first = service.leetcode.sync()
        assert first.records_added == 2

        second = service.leetcode.sync()
        assert second.status.value == "Success"
        assert second.records_added == 0
        assert second.records_skipped == 2

        # Storage counts did not grow.
        problems = service.list_problems()
        submissions = [
            s for p in problems for a in p.attempts for s in a.submissions
        ]
        assert len(problems) == 2
        assert len(submissions) == 2
    finally:
        service.close_storage()


def test_composite_reads_do_not_fall_back_to_the_export_tier(tmp_path: Path):
    """``get_by_slug`` answers from DuckDB only.

    The filesystem tier remains a valid export target — it is just not a source
    of truth, so a row that exists only there must read as absent.
    """
    storage = CompositeStorage(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "data" / "codememory.duckdb",
    )

    # Write through the composite: the row reaches every tier.
    from codememory.domain.enums import DifficultyLevel, SubmissionStatus
    from codememory.domain.models import Attempt, Problem, Submission

    problem = Problem(title="Two Sum", difficulty=DifficultyLevel.EASY, topics=["Array"])
    problem.attempts = [
        Attempt(
            problem_id=problem.id,
            attempt_number=1,
            status=SubmissionStatus.ACCEPTED,
            submissions=[
                Submission(
                    problem_id=problem.id,
                    code="pass",
                    language="python",
                    status=SubmissionStatus.ACCEPTED,
                )
            ],
        )
    ]
    storage.save(problem)

    assert storage.get_by_slug("two-sum") is not None
    assert storage.get_by_id(problem.id) is not None

    # Delete only the canonical row, leaving the export intact.
    storage.duckdb_repo.conn.execute("DELETE FROM problems WHERE id = ?", [problem.id])
    assert storage.fs_repo.get_by_slug("two-sum") is not None

    assert storage.get_by_slug("two-sum") is None
    assert storage.get_by_id(problem.id) is None
    # The export is still readable through its own repository.
    assert storage.fs_repo.get_by_slug("two-sum") is not None


def test_duckdb_does_not_silently_substitute_an_in_memory_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """An unwritable database file must fail loudly, not become ephemeral.

    A second process holding the file lock used to send this server into
    ``:memory:`` — healthy-looking, permanently empty, and lossy. The lock
    itself is a cross-process concern DuckDB owns; what this pins is the
    constructor's response to it: retry read-only, then propagate.
    """
    db_path = tmp_path / "locked.duckdb"
    real_connect = duckdb.connect
    attempts: list[tuple[str, bool]] = []

    def refusing_connect(path, *args, **kwargs):
        attempts.append((str(path), bool(kwargs.get("read_only", False))))
        if str(path) == str(db_path):
            # The shape of error DuckDB raises for a file another process holds.
            raise duckdb.IOException(
                "Cannot open file: The process cannot access the file because it "
                "is being used by another process."
            )
        return real_connect(path, *args, **kwargs)

    monkeypatch.setattr(duckdb, "connect", refusing_connect)

    with pytest.raises(duckdb.IOException):
        DuckDBStorage(db_path=db_path)

    # It tried the file, retried read-only, and never substituted ``:memory:``.
    assert attempts == [(str(db_path), False), (str(db_path), True)]
    assert ":memory:" not in {path for path, _ in attempts}


def test_duckdb_connects_for_real_once_the_lock_is_released(tmp_path: Path):
    """The same path connects and reports healthy when nothing holds it.

    Guards against the fix turning into a blanket refusal to connect.
    """
    storage = DuckDBStorage(db_path=tmp_path / "live.duckdb")
    try:
        assert storage.health() is True
        assert storage.db_path.endswith("live.duckdb")
    finally:
        storage.close()
