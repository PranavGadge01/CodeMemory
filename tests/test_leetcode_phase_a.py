"""Phase A regression tests: data contract, B4, and sync persistence.

Every test in this module is fully mocked. None of them may reach the live
LeetCode network — these are the tests that the original B4 bug escaped because
only the empty-response path was covered.
"""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock
import json
import tempfile

import pytest

from codememory.connectors.account.models import AccountConnection, AccountStatus
from codememory.connectors.account.service import AccountService
from codememory.connectors.base import RawExternalSubmission
from codememory.connectors.leetcode.importer import LeetCodeImporter
from codememory.connectors.leetcode.leetcode_connector import LeetCodeConnector
from codememory.connectors.leetcode.mapper import LeetCodeMapper
from codememory.connectors.leetcode.models import LeetCodeSubmissionRaw
from codememory.connectors.leetcode.parser import LeetCodeParser
from codememory.connectors.leetcode.sync import LeetCodeSyncEngine
from codememory.core.service import CodeMemoryService
from codememory.domain.import_schema import NormalizedSubmissionRecord, normalize_language, parse_memory, parse_runtime, parse_timestamp
from codememory.domain.models import Submission, canonical_timestamp, compute_submission_hash

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "leetcode"


def _raw(**overrides) -> LeetCodeSubmissionRaw:
    """Build a raw LeetCode submission with sensible defaults."""
    base = dict(
        id="111",
        submission_id="111",
        title="Two Sum",
        title_slug="two-sum",
        language="python3",
        status="Accepted",
        timestamp=1700007200,
        runtime="45 ms",
        memory="17.2 MB",
        code="class Solution: pass",
    )
    base.update(overrides)
    return LeetCodeSubmissionRaw(**base)


def _fixture_raw(submission_id: str = "1003") -> LeetCodeSubmissionRaw:
    """Build a raw record whose content is read straight from the fixture file.

    Tests that must hash identically to an imported fixture record cannot use
    _raw()'s hand-typed defaults — a single differing field (most easily ``code``)
    produces a different fingerprint and the comparison becomes meaningless. This
    helper makes the fixture file the single source of truth.
    """
    records = json.loads((FIXTURES_DIR / "sample_leetcode.json").read_text())
    fx = next(r for r in records if r["submission_id"] == submission_id)
    return LeetCodeSubmissionRaw(
        id=fx["submission_id"],
        submission_id=fx["submission_id"],
        title=fx["title"],
        title_slug=fx["title_slug"],
        difficulty=fx.get("difficulty"),
        topics=fx.get("topics", []),
        language=fx["language"],
        code=fx["code"],
        status=fx["status"],
        runtime=fx.get("runtime"),
        memory=fx.get("memory"),
        timestamp=fx.get("timestamp"),
        url=fx.get("url"),
    )


def _make_service(tmp_path: Path, account_service=None) -> CodeMemoryService:
    """Build a fully isolated CodeMemoryService rooted at tmp_path."""
    return CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "phase_a.duckdb",
        account_service=account_service,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1. Field normalization
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw_value,expected_ms",
    [
        ("45 ms", 45.0),
        ("45ms", 45.0),
        ("1 s", 1000.0),
        (45, 45.0),
        (45.5, 45.5),
        ("N/A", None),
        ("", None),
        (None, None),
    ],
)
def test_runtime_normalization(raw_value, expected_ms):
    """Runtime must parse to float milliseconds for every supported spelling."""
    assert parse_runtime(raw_value) == expected_ms


@pytest.mark.parametrize(
    "raw_value,expected_mb",
    [
        ("17.2 MB", 17.2),
        ("2048 KB", 2.0),
        ("1 GB", 1024.0),
        (17.2, 17.2),
        ("N/A", None),
        (None, None),
    ],
)
def test_memory_normalization(raw_value, expected_mb):
    """Memory must parse to float megabytes, with unit conversion."""
    assert parse_memory(raw_value) == expected_mb


@pytest.mark.parametrize(
    "raw_value,expected_iso",
    [
        (1700007200, "2023-11-15T00:13:20+00:00"),          # epoch seconds
        (1700007200000, "2023-11-15T00:13:20+00:00"),      # epoch milliseconds
        ("1700007200", "2023-11-15T00:13:20+00:00"),       # numeric string
        ("2023-11-15T00:13:20Z", "2023-11-15T00:13:20+00:00"),
        ("2023-11-15 00:13:20", "2023-11-15T00:13:20+00:00"),
        ("2023-11-15T05:43:20+05:30", "2023-11-15T00:13:20+00:00"),  # offset preserved as UTC
    ],
)
def test_timestamp_normalization(raw_value, expected_iso):
    """Every supported timestamp spelling must resolve to the same UTC instant."""
    parsed = parse_timestamp(raw_value)
    assert parsed.tzinfo is not None, "parsed timestamp must be timezone-aware"
    # Compare the instant, not the printed offset: parse_timestamp preserves the
    # source offset while canonical_timestamp() collapses it for hashing.
    assert parsed.astimezone(timezone.utc).isoformat() == expected_iso


def test_timestamp_normalization_defaults_to_now():
    """Missing/unparseable timestamps fall back to the current UTC time."""
    before = datetime.now(timezone.utc)
    parsed = parse_timestamp(None)
    after = datetime.now(timezone.utc)
    assert before <= parsed <= after
    assert parsed.tzinfo is not None


def test_canonical_timestamp_is_timezone_stable():
    """A tz-aware UTC datetime and its naive-but-UTC twin hash identically.

    This is what makes deduplication work across the DuckDB read path (naive)
    and the in-memory domain path (tz-aware).
    """
    aware = datetime(2023, 11, 15, 0, 13, 20, tzinfo=timezone.utc)
    naive = datetime(2023, 11, 15, 0, 13, 20)
    assert canonical_timestamp(aware) == canonical_timestamp(naive)
    assert canonical_timestamp(1700007200) == canonical_timestamp(aware)


@pytest.mark.parametrize(
    "raw_lang,expected",
    [
        ("python3", "Python"),
        ("python", "Python"),
        ("cpp", "C++"),
        ("golang", "Go"),
        ("javascript", "JavaScript"),
        ("csharp", "C#"),
        ("PHP", "PHP"),          # unknown spellings pass through, not force-capitalized
        ("", "Unknown"),
        (None, "Unknown"),
    ],
)
def test_language_normalization(raw_lang, expected):
    assert normalize_language(raw_lang) == expected


def test_difficulty_defaults_to_unknown():
    """Absent/unrecognized difficulty must never silently become Medium."""
    assert LeetCodeMapper.normalize_difficulty(None) == "Unknown"
    assert LeetCodeMapper.normalize_difficulty("") == "Unknown"
    assert LeetCodeMapper.normalize_difficulty("Bogus") == "Unknown"
    assert LeetCodeMapper.normalize_difficulty("Easy") == "Easy"
    assert LeetCodeMapper.normalize_difficulty("hard") == "Hard"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Canonical identity and hash
# ─────────────────────────────────────────────────────────────────────────────


def test_stable_external_submission_id():
    """The LeetCode submission id is preserved as the stored record identity."""
    norm = LeetCodeMapper.to_normalized_record(_raw())
    assert norm.submission_id == "leetcode_111"
    assert norm.problem_id == "two-sum"  # authoritative titleSlug, not a title guess


def test_external_id_falls_back_to_primary_id():
    norm = LeetCodeMapper.to_normalized_record(_raw(submission_id=None))
    assert norm.submission_id == "leetcode_111"


def test_problem_id_falls_back_to_generated_slug():
    """Without a titleSlug, identity degrades to a slug derived from the title."""
    norm = LeetCodeMapper.to_normalized_record(_raw(title_slug=None))
    assert norm.problem_id == "two-sum"


def test_canonical_hash_is_deterministic():
    norm = LeetCodeMapper.to_normalized_record(_raw())
    again = LeetCodeMapper.to_normalized_record(_raw())
    assert norm.submission_hash == again.submission_hash
    assert len(norm.submission_hash) == 64  # SHA-256 hex


def test_hash_differs_for_different_code():
    a = LeetCodeMapper.to_normalized_record(_raw(code="class Solution: pass")
    )
    b = LeetCodeMapper.to_normalized_record(_raw(code="class Solution: return")
    )
    assert a.submission_hash != b.submission_hash


def test_hash_computed_without_code():
    """A code-less record still receives a hash (this is the collision fix)."""
    norm = LeetCodeMapper.to_normalized_record(_raw(code=""))
    assert norm.submission_hash
    assert len(norm.submission_hash) == 64


def test_hash_same_through_every_entry_point():
    """The LeetCode mapper path and the generic import path must agree.

    Requirement 13 of Phase A: the same submission cannot get two different
    fingerprints depending on which door it came in through.
    """
    via_mapper = LeetCodeMapper.to_normalized_record(_raw())

    via_generic, errors = NormalizedSubmissionRecord.__class__, []
    rec = NormalizedSubmissionRecord.model_validate(
        {
            "submission_id": "111",
            "title": "Two Sum",
            "title_slug": "two-sum",
            "language": "python3",
            "status": "Accepted",
            "runtime": "45 ms",
            "memory": "17.2 MB",
            "timestamp": 1700007200,
            "code": "class Solution: pass",
        }
    )
    assert not errors
    assert via_mapper.submission_hash == rec.submission_hash
    assert via_mapper.runtime_ms == rec.runtime_ms == 45.0
    assert via_mapper.memory_mb == rec.memory_mb == 17.2
    assert via_mapper.timestamp == rec.timestamp


def test_domain_submission_always_gets_hash():
    """Submission.model_post_init must never leave an empty hash, code or not."""
    with_code = Submission(problem_id="two-sum", code="x", language="Python", submitted_at="2023-11-15T00:00:00Z", status="Accepted")
    without_code = Submission(problem_id="two-sum", code="", language="Python", submitted_at="2023-11-15T00:00:00Z", status="Accepted")
    assert with_code.submission_hash
    assert without_code.submission_hash
    assert with_code.submission_hash != without_code.submission_hash


def test_single_hash_function():
    """No duplicate hash implementation may survive in the connector layer."""
    assert not hasattr(LeetCodeMapper, "compute_submission_hash")
    assert not hasattr(LeetCodeMapper, "parse_timestamp")
    assert LeetCodeMapper.compute_submission_hash is not compute_submission_hash if hasattr(
        LeetCodeMapper, "compute_submission_hash"
    ) else True


# ─────────────────────────────────────────────────────────────────────────────
# 3. Connector (B4 regression — the non-empty path)
# ─────────────────────────────────────────────────────────────────────────────


class _StubClient:
    """Stand-in for LeetCodeClient returning canned GraphQL payloads."""

    def __init__(self, submissions):
        self.submissions = submissions
        self.calls = 0

    def fetch_user_submissions(self, username, limit=50):
        self.calls += 1
        return self.submissions

    def fetch_problem_details(self, slug):
        return None


def test_connector_empty_response():
    """The previously-tested empty path must keep working."""
    connector = LeetCodeConnector()
    connector.client = _StubClient([])
    assert connector.fetch_user_submissions("someone") == []


def test_connector_single_submission_b4_regression():
    """B4: a NON-EMPTY response must not raise and must round-trip correctly."""
    connector = LeetCodeConnector()
    connector.client = _StubClient([_raw()])

    results = connector.fetch_user_submissions("someone")

    assert len(results) == 1
    item = results[0]
    assert isinstance(item, RawExternalSubmission)
    assert item.external_id == "leetcode_111"
    assert item.problem_slug == "two-sum"
    assert item.status == "Accepted"
    assert item.runtime == "45 ms"
    assert item.memory == "17.2 MB"
    assert item.timestamp == "1700007200"


def test_connector_multiple_submissions():
    connector = LeetCodeConnector()
    connector.client = _StubClient(
        [
            _raw(id="111", submission_id="111"),
            _raw(id="112", submission_id="112", title="3Sum", title_slug="3sum", status="Wrong Answer"),
            _raw(id="113", submission_id="113", title="Two Sum", title_slug="two-sum", language="cpp"),
        ]
    )
    results = connector.fetch_user_submissions("someone", limit=3)
    assert len(results) == 3
    assert [r.external_id for r in results] == ["leetcode_111", "leetcode_112", "leetcode_113"]
    assert [r.problem_slug for r in results] == ["two-sum", "3sum", "two-sum"]


def test_connector_missing_optional_fields():
    """Optional fields absent from the API payload must not break the connector."""
    connector = LeetCodeConnector()
    connector.client = _StubClient([_raw(runtime=None, memory=None, difficulty=None, url=None, topics=[])])

    results = connector.fetch_user_submissions("someone")
    norm = connector.normalize_submission(results[0])

    assert norm.runtime_ms is None
    assert norm.memory_mb is None
    assert norm.difficulty.value == "Unknown"
    assert "leetcode.com" in norm.url  # URL synthesized from the slug


def test_connector_normalize_preserves_identity_and_metrics():
    connector = LeetCodeConnector()
    connector.client = _StubClient([_raw()])
    raw = connector.fetch_user_submissions("someone")[0]
    norm = connector.normalize_submission(raw)

    assert norm.submission_id == "leetcode_111"
    assert norm.problem_id == "two-sum"
    assert norm.runtime_ms == 45.0
    assert norm.memory_mb == 17.2
    assert norm.timestamp.tzinfo is not None
    assert norm.timestamp.isoformat() == "2023-11-15T00:13:20+00:00"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Parser robustness
# ─────────────────────────────────────────────────────────────────────────────


def test_parser_rejects_record_missing_required_fields():
    records, errors = LeetCodeParser.parse_records(
        [
            {"title": "Two Sum"},                       # missing language + status
            {"language": "python3", "status": "Accepted"},  # missing title
            {"title": "OK", "language": "py", "status": "Accepted"},
        ]
    )
    assert len(records) == 1
    assert len(errors) == 2
    assert all("Missing" in e for e in errors)


def test_parser_does_not_treat_question_id_as_submission_id():
    """question_id identifies the problem and must not become the submission id."""
    records, errors = LeetCodeParser.parse_records(
        [{"title": "Two Sum", "language": "python3", "status": "Accepted", "question_id": "1"}]
    )
    assert not errors
    norm = LeetCodeMapper.to_normalized_record(records[0])
    assert norm.submission_id is None  # no real submission id available
    assert norm.problem_id == "two-sum"


# ─────────────────────────────────────────────────────────────────────────────
# 5. Persistence: idempotency and code-less survival
# ─────────────────────────────────────────────────────────────────────────────


def test_repeated_file_import_is_idempotent(tmp_path):
    storage = _make_service(tmp_path).storage
    importer = LeetCodeImporter(storage=storage)

    first = importer.import_file(FIXTURES_DIR / "sample_leetcode.json")
    assert first.imported_count == 6
    assert first.duplicate_count == 0

    second = importer.import_file(FIXTURES_DIR / "sample_leetcode.json")
    assert second.imported_count == 0
    assert second.duplicate_count == 6

    total = sum(len([s for a in p.attempts for s in a.submissions]) for p in storage.list_all())
    assert total == 6  # nothing duplicated


def test_imported_submission_ids_and_metrics_survive_reload(tmp_path):
    storage = _make_service(tmp_path).storage
    LeetCodeImporter(storage=storage).import_file(FIXTURES_DIR / "sample_leetcode.json")

    two_sum = storage.get_by_slug("two-sum")
    subs = sorted(
        [s for a in two_sum.attempts for s in a.submissions],
        key=lambda s: s.submitted_at,
    )
    assert [s.id for s in subs] == ["leetcode_1001", "leetcode_1002", "leetcode_1003"]
    accepted = next(s for s in subs if s.status.value == "Accepted")
    assert accepted.runtime_ms == 45.0
    assert accepted.memory_mb == 17.2
    assert accepted.submitted_at.tzinfo is not None
    assert accepted.submitted_at.astimezone(timezone.utc).isoformat() == "2023-11-15T00:13:20+00:00"


def test_code_less_submissions_do_not_collapse(tmp_path):
    """Two code-less submissions on different problems must both survive.

    Pre-Phase A they shared an empty hash and the UNIQUE constraint silently
    merged them into a single row — data loss across the whole database.
    """
    service = _make_service(tmp_path)
    service.add_problem(title="Alpha", slug="alpha")
    service.add_problem(title="Beta", slug="beta")
    service.add_submission(problem_identifier="alpha", code="", language="Python", status="Accepted", submitted_at="2023-11-01T10:00:00Z")
    service.add_submission(problem_identifier="beta", code="", language="Python", status="Accepted", submitted_at="2023-11-02T10:00:00Z")

    stored = sum(len([s for a in p.attempts for s in a.submissions]) for p in service.list_problems())
    assert stored == 2


def test_code_less_submissions_same_problem_stay_distinct(tmp_path):
    service = _make_service(tmp_path)
    service.add_problem(title="Gamma", slug="gamma")
    service.add_submission(problem_identifier="gamma", code="", language="Python", status="Wrong Answer", submitted_at="2023-11-01T10:00:00Z")
    service.add_submission(problem_identifier="gamma", code="", language="Python", status="Accepted", submitted_at="2023-11-02T10:00:00Z")

    gamma = service.get_problem("gamma")
    assert len([s for a in gamma.attempts for s in a.submissions]) == 2


def test_add_submission_is_idempotent_by_hash(tmp_path):
    """add_submission() must not duplicate an already stored submission."""
    service = _make_service(tmp_path)
    service.add_problem(title="Delta", slug="delta")

    _, first = service.add_submission(
        problem_identifier="delta",
        code="def solve(): pass",
        language="Python",
        status="Accepted",
        submitted_at="2023-11-01T10:00:00Z",
        submission_id="leetcode_500",
    )
    _, again = service.add_submission(
        problem_identifier="delta",
        code="def solve(): pass",
        language="Python",
        status="Accepted",
        submitted_at="2023-11-01T10:00:00Z",
        submission_id="leetcode_500",
    )
    assert first.id == again.id == "leetcode_500"

    delta = service.get_problem("delta")
    assert len([s for a in delta.attempts for s in a.submissions]) == 1


def test_timestamp_round_trips_through_storage_without_tz_shift(tmp_path):
    """Regression for the local-timezone binding bug in the DuckDB tier."""
    service = _make_service(tmp_path)
    service.add_problem(title="Epsilon", slug="epsilon")
    service.add_submission(
        problem_identifier="epsilon",
        code="pass",
        language="Python",
        status="Accepted",
        submitted_at="2023-11-15T00:13:20+00:00",
    )
    eps = service.get_problem("epsilon")
    stored = eps.attempts[-1].submissions[-1]
    assert stored.submitted_at.isoformat() == "2023-11-15T00:13:20+00:00"


def test_legacy_empty_hash_is_repaired_without_data_loss(tmp_path):
    """A database containing legacy empty-hash rows is repaired on open.

    Rows keep the canonical hash when it is free; otherwise they fall back to a
    unique legacy placeholder so no record is ever deleted or merged.
    """
    service = _make_service(tmp_path)
    service.add_problem(title="Legacy", slug="legacy")
    service.add_submission(
        problem_identifier="legacy",
        code="def solve(): pass",
        language="Python",
        status="Accepted",
        submitted_at="2023-11-01T10:00:00Z",
    )

    # Simulate a pre-Phase A row: an empty hash written straight into DuckDB.
    service.storage.duckdb_repo.conn.execute(
        "UPDATE submissions SET submission_hash = '' WHERE 1=1"
    )
    assert service.storage.duckdb_repo.conn.execute(
        "SELECT count(*) FROM submissions WHERE submission_hash = ''"
    ).fetchone()[0] == 1

    # Re-open storage on the same database file, which triggers the repair.
    reopened = _make_service(tmp_path)
    empty = reopened.storage.duckdb_repo.conn.execute(
        "SELECT count(*) FROM submissions WHERE submission_hash = '' OR submission_hash IS NULL"
    ).fetchone()[0]
    assert empty == 0
    assert len(reopened.storage.list_all()) == 1  # data preserved, nothing merged away


# ─────────────────────────────────────────────────────────────────────────────
# 6. Live sync against a real storage tier (mocked client only)
# ─────────────────────────────────────────────────────────────────────────────


def _connected_engine(tmp_path: Path, client) -> tuple[LeetCodeSyncEngine, CodeMemoryService]:
    acct = AccountService(data_dir=tmp_path / "accounts")
    acct.save_connection(AccountConnection(provider="LeetCode", username="syncuser", status=AccountStatus.CONNECTED))
    service = _make_service(tmp_path, account_service=acct)
    engine = LeetCodeSyncEngine(account_service=acct, client=client)
    return engine, service


def _profile_client(submissions) -> MagicMock:
    client = MagicMock()
    client.fetch_user_profile.return_value = {
        "username": "syncuser",
        "real_name": "Sync User",
        "solved_all": 1,
    }
    client.fetch_user_submissions.return_value = submissions
    client.fetch_problem_details.return_value = None
    return client


def test_initial_sync_persists_identity_and_timestamp(tmp_path):
    engine, service = _connected_engine(tmp_path, _profile_client([_raw()]))
    result = engine.sync(service)

    assert result.records_added == 1
    assert result.records_failed == 0

    stored = [s for a in service.get_problem("two-sum").attempts for s in a.submissions]
    assert len(stored) == 1
    assert stored[0].id == "leetcode_111"
    assert stored[0].submitted_at.tzinfo is not None
    assert stored[0].submitted_at.isoformat() == "2023-11-15T00:13:20+00:00"
    assert stored[0].language == "Python"


def test_repeated_sync_of_identical_submission(tmp_path):
    """The core Phase A idempotency guarantee for the sync path."""
    engine, service = _connected_engine(tmp_path, _profile_client([_raw()]))

    first = engine.sync(service)
    second = engine.sync(service)

    assert first.records_added == 1
    assert second.records_added == 0
    assert second.records_skipped == 1
    assert second.records_failed == 0

    stored = [s for a in service.get_problem("two-sum").attempts for s in a.submissions]
    assert len(stored) == 1


def test_sync_then_import_same_submission_is_idempotent(tmp_path):
    """A submission synced live with its real code must not be re-imported."""
    synced = _fixture_raw("1003")
    engine, service = _connected_engine(tmp_path, _profile_client([synced]))
    engine.sync(service)

    importer = LeetCodeImporter(storage=service.storage)
    summary = importer.import_file(FIXTURES_DIR / "sample_leetcode.json")

    # The synced record occupies the canonical hash of fixture record 1003, so
    # only the other five are new.
    assert summary.imported_count == 5
    assert summary.duplicate_count == 1

    stored = sorted(
        s.id for a in service.get_problem("two-sum").attempts for s in a.submissions
    )
    assert stored == ["leetcode_1001", "leetcode_1002", "leetcode_1003"]


def test_sync_without_code_then_import_refreshes_in_place(tmp_path):
    """A code-less sync record is refreshed by a later import, never duplicated.

    The synced placeholder and the file record share the external id but not the
    hash. The storage upsert keys on the external id, so the import updates the
    existing row instead of creating a second one.
    """
    synced = _raw(id="1003", submission_id="1003", code="")
    engine, service = _connected_engine(tmp_path, _profile_client([synced]))
    engine.sync(service)

    importer = LeetCodeImporter(storage=service.storage)
    importer.import_file(FIXTURES_DIR / "sample_leetcode.json")

    two_sum = service.get_problem("two-sum")
    stored = [s for a in two_sum.attempts for s in a.submissions]
    assert len(stored) == 3, "no duplicate rows may be created"
    refreshed = next(s for s in stored if s.id == "leetcode_1003")
    assert refreshed.code.startswith("class Solution")
    assert refreshed.runtime_ms == 45.0
    assert refreshed.memory_mb == 17.2


def test_sync_with_new_submission_after_partial_failure(tmp_path):
    """A submission that fails once must still import on the next sync."""
    submissions = [_raw(), _raw(id="112", submission_id="112", title="3Sum", title_slug="3sum")]

    engine, service = _connected_engine(tmp_path, _profile_client(submissions))
    first = engine.sync(service)
    assert first.records_added == 2

    # Second sync reports the same two as skipped and nothing new is written.
    second = engine.sync(service)
    assert second.records_added == 0
    assert second.records_skipped == 2
    assert sum(len([s for a in p.attempts for s in a.submissions]) for p in service.list_problems()) == 2


def test_sync_handles_empty_submission_list(tmp_path):
    engine, service = _connected_engine(tmp_path, _profile_client([]))
    result = engine.sync(service)
    assert result.records_discovered == 0
    assert result.records_added == 0
    assert result.records_failed == 0


def test_sync_skips_submission_already_present_by_external_id(tmp_path):
    """Dedup must also key on the external id, not only on the hash."""
    service = _make_service(tmp_path)
    service.add_problem(title="Two Sum", slug="two-sum", url="https://leetcode.com/problems/two-sum/")
    # Persist the same external id with *different* code: the hash will differ,
    # so only the external-id check can prevent the duplicate.
    service.add_submission(
        problem_identifier="two-sum",
        code="def different(): pass",
        language="Python",
        status="Accepted",
        submitted_at="2023-11-15T00:13:20+00:00",
        submission_id="leetcode_111",
    )

    engine, _ = _connected_engine(tmp_path, _profile_client([_raw()]))
    engine.account_service.save_connection(
        AccountConnection(provider="LeetCode", username="syncuser", status=AccountStatus.CONNECTED)
    )
    result = engine.sync(service)

    assert result.records_added == 0
    assert result.records_skipped == 1
    stored = [s for a in service.get_problem("two-sum").attempts for s in a.submissions]
    assert len(stored) == 1
    assert stored[0].id == "leetcode_111"


# ─────────────────────────────────────────────────────────────────────────────
# 7. Cross-path dedup
# ─────────────────────────────────────────────────────────────────────────────


def test_same_submission_through_import_and_connector_paths(tmp_path):
    """The connector's normalized record and the file importer's must hash alike."""
    connector = LeetCodeConnector()
    connector.client = _StubClient([_fixture_raw("1003")])
    via_connector = connector.normalize_submission(connector.fetch_user_submissions("u")[0])

    via_importer, _ = LeetCodeImporter(storage=_make_service(tmp_path).storage).parse_and_normalize(
        FIXTURES_DIR / "sample_leetcode.json"
    )
    fixture_accepted = next(r for r in via_importer if r.submission_id == "leetcode_1003")

    assert via_connector.submission_hash == fixture_accepted.submission_hash
    assert via_connector.runtime_ms == fixture_accepted.runtime_ms
    assert via_connector.memory_mb == fixture_accepted.memory_mb
