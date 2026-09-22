"""Phase 1: LeetCode multi-account data provenance tests.

These verify that:
- Submissions are persisted with source_provider / source_account.
- Same-account sync remains idempotent.
- Different accounts do not cross-deduplicate.
- Connecting B does not delete A's historical submissions.
- Analytics account filtering works.
- Disconnecting preserves historical data.
- Existing tests continue to pass.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from codememory.connectors.account.service import AccountService
from codememory.connectors.leetcode.models import LeetCodeSubmissionRaw
from codememory.connectors.leetcode.service import LeetCodeAccountService
from codememory.core.service import CodeMemoryService
from codememory.domain.enums import SubmissionStatus
from codememory.domain.models import Submission


def _raw(
    submission_id: str = "111",
    title: str = "Two Sum",
    slug: str = "two-sum",
    timestamp: int = 1700000000,
    status: str = "Accepted",
    language: str = "python3",
) -> LeetCodeSubmissionRaw:
    return LeetCodeSubmissionRaw(
        id=submission_id,
        submission_id=submission_id,
        title=title,
        title_slug=slug,
        language=language,
        status=status,
        timestamp=timestamp,
    )


def _mock_client(submissions=None, *, username="syncuser"):
    """A transport stub returning a profile and optional submissions for any username."""
    client = MagicMock()
    client.fetch_user_profile.return_value = {
        "username": username,
        "real_name": username,
        "user_avatar": None,
        "ranking": 9999,
        "solved_all": 1,
        "solved_easy": 1,
        "solved_medium": 0,
        "solved_hard": 0,
    }
    client.fetch_user_submissions.return_value = (
        [_raw()] if submissions is None else submissions
    )
    client.fetch_problem_details.return_value = None
    return client


def _make_service(tmp_path: Path) -> CodeMemoryService:
    return CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "test_ma.duckdb",
    )


def _surface(tmp_path: Path, client=None) -> tuple[LeetCodeAccountService, CodeMemoryService]:
    service = _make_service(tmp_path)
    surface = LeetCodeAccountService(
        app_service=service,
        account_service=AccountService(data_dir=tmp_path / "accounts"),
        client=client or _mock_client(),
    )
    return surface, service


def _stored_submissions(service: CodeMemoryService):
    return [s for p in service.list_problems() for a in p.attempts for s in a.submissions]


# 1. Existing submissions without provenance still load
def test_legacy_submission_without_provenance_loads(tmp_path):
    """A submission created before the provenance columns exist must still load."""
    service = _make_service(tmp_path)
    problem = service.add_problem(
        title="Legacy Problem", slug="legacy", difficulty="Easy", topics=[],
        url=None, statement=None
    )
    # Insert a legacy record directly via the storage layer — no source fields
    sub = Submission(
        id="legacy_sub_1",
        problem_id=problem.id,
        attempt_id="",
        code="",
        language="python3",
        status=SubmissionStatus.ACCEPTED,
        submitted_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        error_message=None,
        submission_hash="legacy_hash_1",
    )
    service.storage.save_submission(sub)

    subs = _stored_submissions(service)
    assert len(subs) == 1
    assert subs[0].source_provider is None
    assert subs[0].source_account is None


# 2. New LeetCode submission contains source_provider + source_account
def test_sync_tags_submission_with_provided_account(tmp_path):
    """A LeetCode-synced submission is tagged with provider and username."""
    client = _mock_client([_raw()], username="alice")
    surface, service = _surface(tmp_path, client)
    surface.connect("alice")
    surface.sync()

    subs = _stored_submissions(service)
    assert len(subs) == 1
    assert subs[0].source_provider == "leetcode"
    assert subs[0].source_account == "alice"


# 3. Same account syncing the same submission remains idempotent
def test_same_account_sync_is_idempotent(tmp_path):
    """Resyncing the same account for the same window does not duplicate."""
    client = _mock_client([_raw()], username="alice")
    surface, service = _surface(tmp_path, client)
    surface.connect("alice")

    first = surface.sync()
    second = surface.sync()

    assert first.records_added == 1
    assert second.records_added == 0
    assert second.records_skipped == 1
    assert len(_stored_submissions(service)) == 1


# 4. Account A and B can store equivalent submissions without cross-account deduplication
def test_different_accounts_do_not_cross_dedup(tmp_path):
    """Two accounts solving the same problem at the same time both get stored.

    In reality LeetCode assigns globally-unique submission IDs, so A and B have
    different IDs even for the same problem. We simulate that here: both have
    the same slug/timestamp/language/status but different submission IDs, so the
    only thing that prevents cross-account dedup is the hash including the
    source_account.
    """
    raw_a = _raw(submission_id="200", timestamp=1700000000)
    raw_b = _raw(submission_id="201", timestamp=1700000000)  # same problem, same time, different ID

    # Account A
    client_a = _mock_client([raw_a], username="alice")
    surface_a, service_a = _surface(tmp_path, client_a)
    surface_a.connect("alice")
    surface_a.sync()

    # Account B — same tmp_path so they share DuckDB; fresh AccountService = fresh watermark
    client_b = _mock_client([raw_b], username="bob")
    surface_b, service_b = _surface(tmp_path, client_b)
    surface_b.connect("bob")
    surface_b.sync()

    subs = _stored_submissions(service_b)
    assert len(subs) == 2

    alice_subs = [s for s in subs if s.source_account == "alice"]
    bob_subs = [s for s in subs if s.source_account == "bob"]
    assert len(alice_subs) == 1
    assert len(bob_subs) == 1
    # Hashes differ because source_account is part of the hash
    assert alice_subs[0].submission_hash != bob_subs[0].submission_hash


# 5. Connecting B does not delete A's historical submissions
def test_connect_b_preserves_a_submissions(tmp_path):
    """Connecting account B after A must not delete A's submissions."""
    raw = _raw(submission_id="300", timestamp=1700000000)
    client_a = _mock_client([raw], username="alice")
    surface_a, service_a = _surface(tmp_path, client_a)
    surface_a.connect("alice")
    surface_a.sync()

    alice_before = _stored_submissions(service_a)
    assert len(alice_before) == 1
    assert alice_before[0].source_account == "alice"

    # Now connect B with a different problem
    client_b = _mock_client(
        [_raw(submission_id="301", title="Add Two", slug="add-two", timestamp=1700003600)],
        username="bob"
    )
    surface_b, service_b = _surface(tmp_path, client_b)
    surface_b.connect("bob")
    surface_b.sync()

    all_subs = _stored_submissions(service_b)
    assert len(all_subs) == 2
    accounts = {s.source_account for s in all_subs}
    assert accounts == {"alice", "bob"}


# 6. A's historical submissions remain unchanged
def test_a_submissions_unchanged_after_b_connect(tmp_path):
    """After connecting B, A's submissions retain their provenance and data."""
    raw = _raw(submission_id="400", timestamp=1700000000)
    client_a = _mock_client([raw], username="alice")
    surface_a, service_a = _surface(tmp_path, client_a)
    surface_a.connect("alice")
    surface_a.sync()

    alice_sub = _stored_submissions(service_a)[0]
    alice_sub_id = alice_sub.id
    alice_sub_hash = alice_sub.submission_hash

    client_b = _mock_client(
        [_raw(submission_id="401", title="Add Two", slug="add-two", timestamp=1700003600)],
        username="bob"
    )
    surface_b, service_b = _surface(tmp_path, client_b)
    surface_b.connect("bob")
    surface_b.sync()

    all_subs = _stored_submissions(service_b)
    a_subs = [s for s in all_subs if s.source_account == "alice"]
    assert len(a_subs) == 1
    assert a_subs[0].id == alice_sub_id
    assert a_subs[0].submission_hash == alice_sub_hash
    assert a_subs[0].source_provider == "leetcode"
    assert a_subs[0].source_account == "alice"


# 7. Analytics account filter: account="A" → only A's submissions (heatmap)
# 8. Analytics account filter: account="B" → only B's submissions (heatmap)
#    (9. account=None preserves existing aggregate behavior)
def test_analytics_heatmap_filtered_by_account(tmp_path):
    from codememory.analytics.analytics_service import AnalyticsService

    service = _make_service(tmp_path)
    service.add_problem(
        title="Two Sum", slug="two-sum", difficulty="Easy", topics=["Array"],
        url=None, statement=None
    )

    from datetime import timedelta
    recent = datetime.now(timezone.utc) - timedelta(days=1)

    service.add_submission(
        problem_identifier="two-sum",
        code="", language="python3", status="Accepted",
        submitted_at=recent,
        submission_id="leetcode_501", submission_hash=None,
        source_provider="leetcode", source_account="alice",
    )
    service.add_submission(
        problem_identifier="two-sum",
        code="", language="python3", status="Accepted",
        submitted_at=recent,
        submission_id="leetcode_502", submission_hash=None,
        source_provider="leetcode", source_account="bob",
    )

    analytics = AnalyticsService(storage=service.storage)

    all_activity = analytics.get_activity_heatmap(days=90)
    assert len(all_activity) == 1
    assert all_activity[0].submissions == 2

    alice_activity = analytics.get_activity_heatmap(days=90, account="alice")
    assert len(alice_activity) == 1
    assert alice_activity[0].submissions == 1

    bob_activity = analytics.get_activity_heatmap(days=90, account="bob")
    assert len(bob_activity) == 1
    assert bob_activity[0].submissions == 1


def test_analytics_streaks_filtered_by_account(tmp_path):
    from codememory.analytics.analytics_service import AnalyticsService

    service = _make_service(tmp_path)
    service.add_problem(
        title="Two Sum", slug="two-sum", difficulty="Easy", topics=["Array"],
        url=None, statement=None
    )
    service.add_submission(
        problem_identifier="two-sum",
        code="", language="python3", status="Accepted",
        submitted_at=datetime.now(timezone.utc),
        submission_id="leetcode_601", submission_hash=None,
        source_provider="leetcode", source_account="alice",
    )

    service.add_problem(
        title="Add Two", slug="add-two", difficulty="Easy", topics=["Array"],
        url=None, statement=None
    )
    service.add_submission(
        problem_identifier="add-two",
        code="", language="python3", status="Accepted",
        submitted_at=datetime.now(timezone.utc),
        submission_id="leetcode_602", submission_hash=None,
        source_provider="leetcode", source_account="bob",
    )

    analytics = AnalyticsService(storage=service.storage)

    alice_streaks = analytics.get_streaks(account="alice")
    bob_streaks = analytics.get_streaks(account="bob")
    no_filter = analytics.get_streaks()

    assert alice_streaks.current_streak_days >= 1
    assert bob_streaks.current_streak_days >= 1


def test_analytics_timeline_filtered_by_account(tmp_path):
    from codememory.analytics.analytics_service import AnalyticsService

    service = _make_service(tmp_path)
    service.add_problem(
        title="Two Sum", slug="two-sum", difficulty="Easy", topics=["Array"],
        url=None, statement=None
    )
    service.add_problem(
        title="Add Two", slug="add-two", difficulty="Easy", topics=["Array"],
        url=None, statement=None
    )

    service.add_submission(
        problem_identifier="two-sum",
        code="", language="python3", status="Accepted",
        submitted_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        submission_id="leetcode_701", submission_hash=None,
        source_provider="leetcode", source_account="alice",
    )
    service.add_submission(
        problem_identifier="add-two",
        code="", language="python3", status="Accepted",
        submitted_at=datetime(2024, 1, 16, 12, 0, 0, tzinfo=timezone.utc),
        submission_id="leetcode_702", submission_hash=None,
        source_provider="leetcode", source_account="bob",
    )

    analytics = AnalyticsService(storage=service.storage)

    all_timeline = analytics.get_timeline_events(limit=14)
    alice_timeline = analytics.get_timeline_events(limit=14, account="alice")
    bob_timeline = analytics.get_timeline_events(limit=14, account="bob")

    all_solved = {e.title for e in all_timeline if e.kind == "solved"}
    assert "Solved Two Sum" in all_solved
    assert "Solved Add Two" in all_solved

    alice_solved = {e.title for e in alice_timeline if e.kind == "solved"}
    assert alice_solved == {"Solved Two Sum"}

    bob_solved = {e.title for e in bob_timeline if e.kind == "solved"}
    assert bob_solved == {"Solved Add Two"}


def test_analytics_account_none_aggregates_all(tmp_path):
    from codememory.analytics.analytics_service import AnalyticsService

    service = _make_service(tmp_path)
    service.add_problem(
        title="Problem A", slug="problem-a", difficulty="Easy", topics=[],
        url=None, statement=None
    )
    service.add_problem(
        title="Problem B", slug="problem-b", difficulty="Easy", topics=[],
        url=None, statement=None
    )

    service.add_submission(
        problem_identifier="problem-a",
        code="code_a", language="python3", status="Accepted",
        submitted_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        source_provider="leetcode", source_account="alice",
    )
    service.add_submission(
        problem_identifier="problem-b",
        code="code_b", language="python3", status="Accepted",
        submitted_at=datetime(2024, 1, 16, 12, 0, 0, tzinfo=timezone.utc),
        source_provider="leetcode", source_account="bob",
    )

    analytics = AnalyticsService(storage=service.storage)
    overview = analytics.get_overview()
    assert overview.total_submissions == 2
    assert overview.accepted_problems == 2


# 10. Disconnecting an account does not delete its historical submissions
def test_disconnect_preserves_submissions(tmp_path):
    """Disconnect removes connection metadata, not imported submissions."""
    client = _mock_client([_raw()], username="alice")
    surface, service = _surface(tmp_path, client)
    surface.connect("alice")
    surface.sync()

    assert len(_stored_submissions(service)) == 1

    surface.disconnect()

    # Connection record is gone
    assert surface.is_connected() is False
    # But submissions remain
    assert len(_stored_submissions(service)) == 1


# 11. Same-account sync is idempotent (hash + account both match)
def test_same_account_sync_idempotency(tmp_path):
    """A second sync of the same account for the same submission is skipped."""
    client = _mock_client([_raw()])
    surface, service = _surface(tmp_path, client)
    surface.connect("alice")

    first = surface.sync()
    second = surface.sync()

    assert first.records_added == 1
    assert second.records_added == 0
    assert second.records_skipped == 1
    assert len(_stored_submissions(service)) == 1
