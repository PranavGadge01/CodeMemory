"""Phase B sync-contract tests.

Every assertion here is about the honest contract: the public LeetCode API
exposes a server-bounded recent window of accepted submissions with no code, no
runtime and no memory. Sync must persist exactly that — nothing fabricated — and
must never claim completeness.

Fully mocked; no test in this module reaches the network.
"""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock
import tempfile

import pytest

from codememory.connectors.account.models import AccountConnection, AccountStatus, SyncState
from codememory.connectors.account.service import AccountService
from codememory.connectors.leetcode.capabilities import LEETCODE_CAPABILITY_EXPLANATIONS
from codememory.connectors.leetcode.client import LeetCodeClient
from codememory.connectors.leetcode.models import LeetCodeSubmissionRaw
from codememory.connectors.leetcode.sync import (
    DEFAULT_SYNC_LIMIT,
    UNAVAILABLE_FIELDS,
    LeetCodeSyncEngine,
)
from codememory.core.service import CodeMemoryService


def _raw(**overrides) -> LeetCodeSubmissionRaw:
    """Build a raw LeetCode submission shaped like the real API response.

    The public ``recentAcSubmissionList`` returns id/title/titleSlug/timestamp/
    statusDisplay/lang — critically NO code, runtime or memory. The client
    constructs raw records from exactly those fields, so ``code`` is left absent
    here too and takes its empty default.
    """
    base = dict(
        id="111",
        submission_id="111",
        title="Two Sum",
        title_slug="two-sum",
        language="python3",
        status="Accepted",
        timestamp=1700007200,
        runtime=None,
        memory=None,
    )
    base.update(overrides)
    return LeetCodeSubmissionRaw(**base)


def _make_service(tmp_path: Path) -> CodeMemoryService:
    return CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "phase_b.duckdb",
    )


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


def _connected_engine(tmp_path: Path, client) -> tuple[LeetCodeSyncEngine, CodeMemoryService, AccountService]:
    service = _make_service(tmp_path)
    acct = AccountService(data_dir=tmp_path / "accounts")
    acct.save_connection(
        AccountConnection(provider="LeetCode", username="syncuser", status=AccountStatus.CONNECTED)
    )
    engine = LeetCodeSyncEngine(account_service=acct, client=client)
    return engine, service, acct


def _stored_submissions(service: CodeMemoryService) -> list:
    return [s for p in service.list_problems() for a in p.attempts for s in a.submissions]


# ─────────────────────────────────────────────────────────────────────────────
# 1. No fabricated fields
# ─────────────────────────────────────────────────────────────────────────────


def test_no_fabricated_code(tmp_path):
    """The API supplies no source code, so none may be invented.

    A placeholder snippet would be stored as if it were the user's solution and
    would corrupt the canonical submission hash.
    """
    engine, service, _ = _connected_engine(tmp_path, _profile_client([_raw()]))
    result = engine.sync(service)

    assert result.status == SyncState.SUCCESS
    subs = _stored_submissions(service)
    assert len(subs) == 1
    assert subs[0].code == "", "synced submissions must carry empty code, never a placeholder"


def test_no_fabricated_runtime_or_memory(tmp_path):
    """Runtime and memory are absent from the API response and must stay absent."""
    engine, service, _ = _connected_engine(tmp_path, _profile_client([_raw()]))
    engine.sync(service)

    sub = _stored_submissions(service)[0]
    assert sub.runtime_ms is None
    assert sub.memory_mb is None


def test_fabricated_code_marker_is_absent_from_storage(tmp_path):
    """The retired placeholder text must never appear in any persisted record."""
    engine, service, _ = _connected_engine(tmp_path, _profile_client([_raw()]))
    engine.sync(service)

    for sub in _stored_submissions(service):
        assert "Synced from LeetCode" not in sub.code
        assert "Title:" not in sub.code


# ─────────────────────────────────────────────────────────────────────────────
# 2. sync_limit
# ─────────────────────────────────────────────────────────────────────────────


def test_sync_limit_defaults_to_twenty():
    """20 is the practical bound the public API actually serves."""
    assert DEFAULT_SYNC_LIMIT == 20
    assert LeetCodeSyncEngine().sync_limit == 20


def test_sync_limit_is_configurable(tmp_path):
    client = _profile_client([_raw()])
    engine, service, _ = _connected_engine(tmp_path, client)
    engine.sync_limit = 5
    engine.sync(service)

    client.fetch_user_submissions.assert_called_once_with("syncuser", limit=5)


def test_sync_limit_used_by_default(tmp_path):
    client = _profile_client([_raw()])
    engine, service, _ = _connected_engine(tmp_path, client)
    engine.sync(service)

    client.fetch_user_submissions.assert_called_once_with("syncuser", limit=20)


def test_sync_limit_overridable_per_call(tmp_path):
    client = _profile_client([_raw()])
    engine, service, _ = _connected_engine(tmp_path, client)
    engine.sync(service, limit=3)

    client.fetch_user_submissions.assert_called_once_with("syncuser", limit=3)


def test_watermark_is_never_sent_to_leetcode(tmp_path):
    """The watermark is local bookkeeping only — the API has no since/after param."""
    client = _profile_client([_raw(), _raw(id="112", submission_id="112", timestamp=1700000000)])
    engine, service, _ = _connected_engine(tmp_path, client)
    engine.sync(service)
    engine.sync(service)

    for call in client.fetch_user_submissions.call_args_list:
        args, kwargs = call
        assert "since" not in kwargs and "after" not in kwargs and "cursor" not in kwargs
        assert tuple(args) == ("syncuser",) and set(kwargs) == {"limit"}


# ─────────────────────────────────────────────────────────────────────────────
# 3. Watermark
# ─────────────────────────────────────────────────────────────────────────────


def _watermark(acct: AccountService) -> dict:
    conn = acct.get_connection("LeetCode")
    assert conn is not None
    return conn.metadata


def test_watermark_created_on_first_sync(tmp_path):
    """The watermark records the newest persisted record as an ordering tuple."""
    client = _profile_client(
        [
            _raw(id="111", submission_id="111", timestamp=1700000000),
            _raw(id="112", submission_id="112", timestamp=1700007200),
        ]
    )
    engine, service, acct = _connected_engine(tmp_path, client)
    engine.sync(service)

    mark = _watermark(acct)
    assert mark["latest_external_id"] == "leetcode_112"
    assert datetime.fromisoformat(mark["latest_persisted_timestamp"]) == datetime.fromtimestamp(
        1700007200, tz=timezone.utc
    )


def test_watermark_advances_to_newer_record(tmp_path):
    client = _profile_client([_raw(id="111", submission_id="111", timestamp=1700000000)])
    engine, service, acct = _connected_engine(tmp_path, client)
    engine.sync(service)
    assert _watermark(acct)["latest_external_id"] == "leetcode_111"

    client.fetch_user_submissions.return_value = [
        _raw(id="111", submission_id="111", timestamp=1700000000),
        _raw(id="112", submission_id="112", timestamp=1700007200),
    ]
    engine.sync(service)
    assert _watermark(acct)["latest_external_id"] == "leetcode_112"


def test_watermark_ties_break_on_external_id(tmp_path):
    """Timestamps are not unique; the external id breaks the tie."""
    client = _profile_client(
        [
            _raw(id="111", submission_id="111", timestamp=1700007200),
            _raw(id="112", submission_id="112", timestamp=1700007200),
        ]
    )
    engine, service, acct = _connected_engine(tmp_path, client)
    engine.sync(service)

    assert _watermark(acct)["latest_external_id"] == "leetcode_112"


def test_watermark_not_advanced_after_persistence_failure(tmp_path):
    """One failed record must freeze the watermark so the next run can retry."""
    client = _profile_client([_raw(id="111", submission_id="111", timestamp=1700000000)])
    engine, service, acct = _connected_engine(tmp_path, client)
    engine.sync(service)
    assert _watermark(acct)["latest_external_id"] == "leetcode_111"

    # Make persistence of the newer record fail; the older one is a skip.
    original = service.add_submission

    def failing_add(*args, **kwargs):
        if kwargs.get("submission_id") == "leetcode_112":
            raise RuntimeError("storage is down")
        return original(*args, **kwargs)

    service.add_submission = failing_add
    client.fetch_user_submissions.return_value = [
        _raw(id="111", submission_id="111", timestamp=1700000000),
        _raw(id="112", submission_id="112", timestamp=1700007200),
    ]
    result = engine.sync(service)

    assert result.records_failed == 1
    assert result.status == SyncState.PARTIAL
    # Watermark preserved, not regressed and not advanced past the failure.
    assert _watermark(acct)["latest_external_id"] == "leetcode_111"


def test_watermark_does_not_regress(tmp_path):
    """A record removed upstream must not make us forget what we already saw."""
    client = _profile_client([_raw(id="112", submission_id="112", timestamp=1700007200)])
    engine, service, acct = _connected_engine(tmp_path, client)
    engine.sync(service)
    assert _watermark(acct)["latest_external_id"] == "leetcode_112"

    # Next window only shows an older record.
    client.fetch_user_submissions.return_value = [
        _raw(id="111", submission_id="111", timestamp=1700000000),
    ]
    engine.sync(service)

    assert _watermark(acct)["latest_external_id"] == "leetcode_112"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Sync state and the coverage contract
# ─────────────────────────────────────────────────────────────────────────────


def test_partial_when_a_record_fails(tmp_path):
    """SUCCESS is only legitimate when every discovered record persisted."""
    client = _profile_client([_raw()])
    engine, service, _ = _connected_engine(tmp_path, client)
    original = service.add_submission

    def failing_add(*args, **kwargs):
        raise RuntimeError("storage is down")

    service.add_submission = failing_add
    result = engine.sync(service)

    assert result.status == SyncState.PARTIAL
    assert result.records_failed == 1
    assert result.records_added == 0


def test_partial_when_profile_fetch_fails(tmp_path):
    """A dead profile fetch must be surfaced, not swallowed."""
    client = _profile_client([_raw()])
    client.fetch_user_profile.return_value = None
    engine, service, _ = _connected_engine(tmp_path, client)

    result = engine.sync(service)

    assert result.status == SyncState.PARTIAL
    assert result.details["profile_fetch_failed"] is True
    assert result.error_message is not None
    # Submissions still landed.
    assert len(_stored_submissions(service)) == 1


def test_success_when_everything_persists(tmp_path):
    engine, service, _ = _connected_engine(tmp_path, _profile_client([_raw()]))
    result = engine.sync(service)

    assert result.status == SyncState.SUCCESS
    assert result.records_failed == 0
    assert result.details["profile_fetch_failed"] is False


def test_details_coverage_contract(tmp_path):
    engine, service, _ = _connected_engine(tmp_path, _profile_client([_raw()]))
    result = engine.sync(service)

    details = result.details
    assert details["coverage"] == "recent-window", "sync must never claim full history"
    assert details["window_limit"] == 20
    assert details["records_in_window"] == 1
    assert details["window_truncated"] is False
    assert details["gap_detected"] is False
    assert details["unavailable_fields"] == UNAVAILABLE_FIELDS


def test_unavailable_fields_are_the_api_blind_spots():
    assert set(UNAVAILABLE_FIELDS) == {"code", "runtime_ms", "memory_mb"}


def test_window_truncated_when_window_is_full(tmp_path):
    """A full window means the server may have more we cannot reach."""
    full_window = [
        _raw(id=str(i), submission_id=str(i), timestamp=1700000000 + i) for i in range(1, 21)
    ]
    engine, service, _ = _connected_engine(tmp_path, _profile_client(full_window))
    result = engine.sync(service)

    assert result.details["records_in_window"] == 20
    assert result.details["window_truncated"] is True


def test_capabilities_explain_the_window_limitation():
    """The capability text must state what the public sync does not cover."""
    text = LEETCODE_CAPABILITY_EXPLANATIONS["recent_submissions"]
    assert "server-bounded" in text
    assert "not a complete history" in text
    assert "code" in text


# ─────────────────────────────────────────────────────────────────────────────
# 5. Gap detection
# ─────────────────────────────────────────────────────────────────────────────


def test_gap_detected_when_window_moves_past_watermark(tmp_path):
    """Older-visible-newer-than-watermark ⇒ records exist that the window can't see."""
    client = _profile_client(
        [
            _raw(id="111", submission_id="111", timestamp=1700000000),
            _raw(id="112", submission_id="112", timestamp=1700003600),
        ]
    )
    engine, service, _ = _connected_engine(tmp_path, client)
    first = engine.sync(service)
    assert first.details["gap_detected"] is False  # no baseline yet

    # The whole window shifted beyond the persisted watermark.
    client.fetch_user_submissions.return_value = [
        _raw(id="121", submission_id="121", timestamp=1700010000),
        _raw(id="122", submission_id="122", timestamp=1700013600),
    ]
    second = engine.sync(service)

    assert second.details["gap_detected"] is True


def test_no_gap_when_window_overlaps_watermark(tmp_path):
    client = _profile_client(
        [
            _raw(id="111", submission_id="111", timestamp=1700000000),
            _raw(id="112", submission_id="112", timestamp=1700003600),
        ]
    )
    engine, service, _ = _connected_engine(tmp_path, client)
    engine.sync(service)

    # Same window again — the oldest visible record is at or before the watermark.
    result = engine.sync(service)
    assert result.details["gap_detected"] is False


def test_gap_detection_never_invokes_private_apis(tmp_path):
    """Detecting a gap must not trigger recovery through unsupported endpoints."""
    client = _profile_client([_raw(id="111", submission_id="111", timestamp=1700000000)])
    engine, service, _ = _connected_engine(tmp_path, client)
    engine.sync(service)

    client.fetch_user_submissions.return_value = [
        _raw(id="121", submission_id="121", timestamp=1700010000),
    ]
    engine.sync(service)

    # No session-gated / private query was attempted in response to the gap.
    assert client.fetch_problem_details.call_count >= 0
    assert not any(
        name in str(client.method_calls) for name in ("submissionList", "session", "cookie")
    )


# ─────────────────────────────────────────────────────────────────────────────
# 6. Downstream refresh
# ─────────────────────────────────────────────────────────────────────────────


def test_no_reindex_when_nothing_added(tmp_path):
    """An unchanged window writes nothing, so rebuilding the index is pure cost."""
    client = _profile_client([_raw()])
    engine, service, _ = _connected_engine(tmp_path, client)

    calls = []
    original_index = service.memory_engine.index_all

    def counting_index(force_rebuild: bool = False):
        calls.append(force_rebuild)
        return original_index(force_rebuild=force_rebuild)

    service.memory_engine.index_all = counting_index

    engine.sync(service)
    assert len(calls) == 1, "first sync adds data and should index once"

    calls.clear()
    result = engine.sync(service)
    assert result.records_added == 0
    assert calls == [], "nothing changed — the index must not be rebuilt"


def test_reindex_runs_when_records_added(tmp_path):
    client = _profile_client([_raw()])
    engine, service, _ = _connected_engine(tmp_path, client)

    calls = []
    original_index = service.memory_engine.index_all
    service.memory_engine.index_all = lambda force_rebuild=False: (
        calls.append(force_rebuild),
        original_index(force_rebuild=force_rebuild),
    )[1]

    result = engine.sync(service)
    assert result.records_added == 1
    assert len(calls) == 1


# ─────────────────────────────────────────────────────────────────────────────
# 7. Idempotency across runs
# ─────────────────────────────────────────────────────────────────────────────


def test_repeated_sync_is_idempotent(tmp_path):
    """The same window synced twice yields one stored submission, not two."""
    client = _profile_client([_raw()])
    engine, service, _ = _connected_engine(tmp_path, client)

    first = engine.sync(service)
    second = engine.sync(service)

    assert first.records_added == 1
    assert second.records_added == 0
    assert second.records_skipped == 1
    assert second.records_failed == 0
    assert len(_stored_submissions(service)) == 1


def test_repeated_sync_of_mixed_window_is_idempotent(tmp_path):
    """New and already-known records in one window: new ones added, rest skipped."""
    client = _profile_client([_raw()])
    engine, service, _ = _connected_engine(tmp_path, client)
    engine.sync(service)

    client.fetch_user_submissions.return_value = [
        _raw(id="111", submission_id="111", timestamp=1700007200),
        _raw(id="113", submission_id="113", title="3Sum", title_slug="3sum", timestamp=1700100000),
    ]
    result = engine.sync(service)

    assert result.records_added == 1
    assert result.records_skipped == 1
    assert len(_stored_submissions(service)) == 2


def test_sync_engine_can_be_constructed_without_account_service():
    """Default construction must not require external wiring."""
    engine = LeetCodeSyncEngine()
    assert isinstance(engine.client, LeetCodeClient)
    assert engine.sync_limit == DEFAULT_SYNC_LIMIT
