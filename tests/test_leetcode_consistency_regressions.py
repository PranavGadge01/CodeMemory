import gc
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from codememory.connectors.account.models import AccountConnection, AccountStatus, SyncState
from codememory.connectors.account.service import AccountService
from codememory.connectors.leetcode.auth_sync import AuthenticatedSyncOrchestrator
from codememory.connectors.leetcode.authenticated_client import AuthenticatedLeetCodeClient
from codememory.connectors.leetcode.models import LeetCodeSubmissionRaw
from codememory.connectors.leetcode.service import LeetCodeAccountService
from codememory.core.service import CodeMemoryService
from codememory.storage.duckdb_repository import DuckDBStorage
from codememory.connectors.leetcode.vault import CredentialVault
from codememory.domain.models import Problem


def _service(tmp_path, username="alice"):
    accounts = AccountService(data_dir=tmp_path / "accounts")
    accounts.save_connection(
        AccountConnection(
            provider="LeetCode",
            username=username,
            status=AccountStatus.CONNECTED,
        )
    )
    service = CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "codememory.duckdb",
        account_service=accounts,
    )
    return service, accounts


def test_full_raw_page_with_one_parse_failure_continues_pagination():
    client = AuthenticatedLeetCodeClient(session_cookie="session", csrf_token="csrf")
    client.execute_query = Mock(
        return_value={
            "data": {
                "submissionList": {
                    "submissions": [
                        {
                            "id": "101",
                            "title": "Good Record",
                            "titleSlug": "good-record",
                            "timestamp": 1_700_000_000,
                            "statusDisplay": "Accepted",
                            "lang": "Python3",
                        },
                        "malformed raw submission",
                    ]
                }
            }
        }
    )

    submissions, has_next, last_key = client.fetch_submissions_page(
        username="alice", limit=2, offset=0
    )

    assert len(submissions) == 1
    assert has_next is True
    assert last_key is None


def test_failed_record_keeps_checkpoint_on_page_and_stops_before_next_page(
    tmp_path,
):
    service, accounts = _service(tmp_path)
    service.add_problem(title="Good Problem", slug="good-problem")
    service.add_problem(title="Bad Problem", slug="bad-problem")
    vault = Mock(spec=CredentialVault)
    vault.retrieve.return_value = ("mock-session", "mock-csrf")
    vault.validate.return_value = True

    good = LeetCodeSubmissionRaw(
        id="201",
        title="Good Problem",
        title_slug="good-problem",
        status="Wrong Answer",
        language="python3",
        timestamp=1_700_000_000,
    )
    failing = LeetCodeSubmissionRaw(
        id="202",
        title="Bad Problem",
        title_slug="bad-problem",
        status="Wrong Answer",
        language="python3",
        timestamp=1_700_000_001,
    )
    mock_client = Mock()
    mock_client.fetch_submissions_page.side_effect = [
        ([good, failing], True, None),
        ([], False, None),
    ]

    with patch(
        "codememory.connectors.leetcode.auth_sync.AuthenticatedLeetCodeClient",
        return_value=mock_client,
    ):
        orchestrator = AuthenticatedSyncOrchestrator(
            account_service=accounts,
            credential_vault=vault,
            rate_limit_delay=0,
        )
        original_mapper = orchestrator._mapper.to_normalized_record

        def map_record(raw, source_account=None):
            if raw.id == "202":
                raise ValueError("controlled mapping failure")
            return original_mapper(raw, source_account=source_account)

        orchestrator._mapper.to_normalized_record = map_record
        result = orchestrator.sync_full_history(service, username="alice")

    assert result.status == SyncState.PARTIAL
    assert result.records_failed == 1
    mock_client.fetch_submissions_page.assert_called_once()
    checkpoint = accounts.get_connection("LeetCode").metadata["auth_sync_last_key"]
    assert checkpoint == "0"


def test_leetcode_service_passes_its_account_store_to_orchestrator(tmp_path):
    _, accounts = _service(tmp_path)
    account_service = LeetCodeAccountService(
        app_service=Mock(), account_service=accounts
    )
    orchestrator = Mock()

    with patch(
        "codememory.connectors.leetcode.service.AuthenticatedSyncOrchestrator",
        return_value=orchestrator,
    ) as orchestrator_class:
        account_service.sync_authenticated_full_history()

    orchestrator_class.assert_called_once_with(
        account_service=accounts,
        account_identifier="alice",
    )
    orchestrator.sync_full_history.assert_called_once()


def test_different_external_ids_with_same_content_remain_distinct(tmp_path):
    service, _ = _service(tmp_path)
    service.add_problem(title="Two Sum", slug="two-sum", difficulty="Easy")
    submitted_at = datetime(2026, 9, 25, tzinfo=timezone.utc)

    first_problem, first = service.add_submission(
        problem_identifier="two-sum",
        code="print(1)",
        language="python3",
        status="Wrong Answer",
        submitted_at=submitted_at,
        submission_id="leetcode_301",
        source_provider="leetcode",
        source_account="alice",
    )
    second_problem, second = service.add_submission(
        problem_identifier="two-sum",
        code="print(1)",
        language="python3",
        status="Wrong Answer",
        submitted_at=submitted_at,
        submission_id="leetcode_302",
        source_provider="leetcode",
        source_account="alice",
    )

    stored = service.storage.get_by_slug("two-sum")
    stored_ids = {
        submission.id
        for attempt in stored.attempts
        for submission in attempt.submissions
    }
    assert first.id != second.id
    assert first_problem.id == second_problem.id
    assert stored_ids == {"leetcode_301", "leetcode_302"}


def test_same_external_id_in_two_accounts_does_not_overwrite_either(tmp_path):
    service, accounts = _service(tmp_path, username="alice")
    service.add_problem(title="Two Sum", slug="two-sum", difficulty="Easy")

    service.add_submission(
        problem_identifier="two-sum",
        code="alice solution",
        language="python3",
        status="Accepted",
        submitted_at=datetime(2026, 9, 25, tzinfo=timezone.utc),
        submission_id="leetcode_401",
        source_provider="leetcode",
        source_account="alice",
    )
    service.add_submission(
        problem_identifier="two-sum",
        code="bob solution",
        language="python3",
        status="Accepted",
        submitted_at=datetime(2026, 9, 25, tzinfo=timezone.utc),
        submission_id="leetcode_401",
        source_provider="leetcode",
        source_account="bob",
    )

    accounts.save_connection(
        AccountConnection(
            provider="LeetCode", username="alice", status=AccountStatus.CONNECTED
        )
    )
    alice_submissions = [
        submission
        for problem in service.list_problems()
        for attempt in problem.attempts
        for submission in attempt.submissions
    ]
    assert len(alice_submissions) == 1
    assert alice_submissions[0].source_account == "alice"

    accounts.save_connection(
        AccountConnection(
            provider="LeetCode", username="bob", status=AccountStatus.CONNECTED
        )
    )
    bob_submissions = [
        submission
        for problem in service.list_problems()
        for attempt in problem.attempts
        for submission in attempt.submissions
    ]
    assert len(bob_submissions) == 1
    assert bob_submissions[0].source_account == "bob"
    assert bob_submissions[0].id != alice_submissions[0].id


def test_collecting_one_shared_storage_wrapper_keeps_other_wrapper_usable(tmp_path):
    db_path = tmp_path / "shared.duckdb"
    first = DuckDBStorage(db_path=db_path)
    second = DuckDBStorage(db_path=db_path)

    first.save(Problem(title="Two Sum", slug="two-sum"))
    del first
    gc.collect()

    assert second.get_by_slug("two-sum") is not None
