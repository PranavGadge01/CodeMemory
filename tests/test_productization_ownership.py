"""Read/write, switching, migration and recovery regressions for private state."""
import shutil
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import duckdb
import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from codememory.connectors.account.models import AccountConnection
from codememory.connectors.account.service import AccountService
from codememory.core.service import CodeMemoryService
from codememory.domain.models import Problem, Attempt, Submission, ProblemNote, RevisionState
from codememory.domain.ownership import UNASSIGNED
from codememory.domain.exceptions import ProblemNotFoundError
from codememory.storage.duckdb_repository import DuckDBStorage


def seed(storage, slug, owners):
    old = datetime.now(timezone.utc) - timedelta(days=30)
    problem = Problem(id=slug, slug=slug, title=slug, difficulty="Easy", topics=["Array"], created_at=old, updated_at=old)
    for i, account in enumerate(owners):
        problem.attempts.append(Attempt(id=f"{slug}-{account}", problem_id=slug,
            source_account=account, attempt_number=i+1, reasoning=f"private-{account}",
            created_at=old, updated_at=old, status="Wrong Answer", submissions=[Submission(
                id=f"sub-{slug}-{account}", problem_id=slug, language="python3", code=f"code_{account}",
                status="Wrong Answer", submitted_at=old, source_provider="leetcode", source_account=account)]))
    storage.save(problem)


@pytest.fixture
def owned(tmp_path):
    accounts = AccountService(tmp_path / "data/accounts")
    accounts.save_connection(AccountConnection(username="alice"))
    service = CodeMemoryService(base_dir=tmp_path / "data", knowledge_dir=tmp_path / "knowledge",
                                db_path=tmp_path / "data/test.duckdb", account_service=accounts)
    seed(service.storage, "shared", ["alice", "bob"])
    seed(service.storage, "bob-only", ["bob"])
    yield service, accounts
    service.close_storage()


def test_review_and_note_read_write_switching(owned):
    service, accounts = owned
    with TestClient(create_app(service)) as client:
        before = service.storage.duckdb_repo.conn.execute("SELECT * FROM submissions ORDER BY id").fetchall()
        bob_before = service.revision_service.get_problem_priority("shared", account="bob")
        service.add_note("shared", "alice-secret")
        assert client.post("/api/v1/revision/shared/reviewed").status_code == 200
        assert client.post("/api/v1/revision/bob-only/reviewed").status_code == 400
        with pytest.raises(ProblemNotFoundError):
            service.add_note("bob-only", "forbidden")
        assert service.get_problem_priority("shared").days_since_last_activity == 0
        assert not service.get_due_problems()
        accounts.save_connection(AccountConnection(username="bob"))
        detail = client.get("/api/v1/problems/shared")
        assert detail.status_code == 200
        assert "alice-secret" not in detail.text and "private-alice" not in detail.text
        assert service.get_problem_priority("shared") == bob_before
        assert {p.slug for p in service.get_due_problems()} == {"shared", "bob-only"}
        service.add_note("shared", "bob-secret")
        service.mark_reviewed("shared")
        accounts.save_connection(AccountConnection(username="alice"))
        assert "bob-secret" not in client.get("/api/v1/problems/shared").text
        after = service.storage.duckdb_repo.conn.execute("SELECT * FROM submissions ORDER BY id").fetchall()
        assert before == after
        assert len(service.storage.get_by_slug("shared").notes) == 4


def test_search_semantic_memory_and_disconnected_reads(owned):
    service, accounts = owned
    service.add_note("shared", "alicesentinel")
    service.memory_index_all()
    assert not service.search(query="bob-only")
    assert not service.semantic_search("code_bob")
    assert service.memory_search("alicesentinel")
    accounts.save_connection(AccountConnection(username="bob"))
    service.add_note("shared", "bob-unique-secret")
    service.memory_index_all()
    assert service.search(query="bob-only")
    assert not service.semantic_search("alicesentinel")
    docs = service.memory_engine._ensure_indexed(account="bob")
    assert docs and all(d.source_account == "bob" for d in docs)
    assert all("alicesentinel" not in d.content and "code_alice" not in d.content for d in docs)
    accounts.remove_connection()
    with TestClient(create_app(service)) as client:
        assert client.get("/api/v1/problems/shared").status_code == 404
        assert client.get("/api/v1/submissions/sub-shared-alice").status_code == 404
        assert client.get("/api/v1/revision").json() == []
    assert not service.search(query="shared")
    assert not service.memory_search("code_alice")


def test_storage_rejects_note_id_owned_by_other_account(owned):
    service, accounts = owned
    note = service.add_note("shared", "original alice note")
    accounts.save_connection(AccountConnection(username="bob"))
    raw = service.storage.get_by_slug("shared")
    raw.notes = [note.model_copy(update={"source_account": "bob", "content": "forged"})]
    with pytest.raises(ValueError, match="Note does not belong"):
        service.storage.save_private_state(raw, "bob")
    assert service.storage.get_by_slug("shared").notes[0].content == "original alice note"


@pytest.mark.parametrize("owners,expected", [(["alice"], "alice"), (["alice", "bob"], UNASSIGNED)])
def test_legacy_migration_backup_and_idempotency(tmp_path, owners, expected):
    original = tmp_path / "seed.duckdb"
    store = DuckDBStorage(original, shared=False)
    seed(store, "legacy", owners)
    problem = store.get_by_slug("legacy")
    problem.notes.append(ProblemNote(id="legacy-note", problem_id=problem.id, content="Keep original note"))
    store.save(problem)
    store.close()
    legacy = tmp_path / "legacy.duckdb"
    shutil.copy2(original, legacy)
    con = duckdb.connect(str(legacy))
    for column in ("source_account", "mistakes_json", "analysis_json"):
        con.execute(f"ALTER TABLE attempts DROP COLUMN {column}")
    con.execute("ALTER TABLE notes DROP COLUMN source_account")
    con.execute("DROP TABLE schema_migrations")
    con.execute("DROP TABLE account_problem_state")
    original_subs = con.execute("SELECT * FROM submissions ORDER BY id").fetchall()
    original_notes = con.execute("SELECT * FROM notes ORDER BY id").fetchall()
    con.close()
    migrated = DuckDBStorage(legacy, shared=False)
    assert migrated.conn.execute("SELECT * FROM submissions ORDER BY id").fetchall() == original_subs
    assert [row[:6] for row in migrated.conn.execute("SELECT * FROM notes ORDER BY id").fetchall()] == original_notes
    assert migrated.get_by_slug("legacy").notes[0].source_account == expected
    assert migrated.get_by_slug("legacy").revision_states[0].source_account == expected
    migrated.close()
    backup = duckdb.connect(str(legacy) + ".pre-ownership-v1.bak", read_only=True)
    assert backup.execute("SELECT * FROM submissions ORDER BY id").fetchall() == original_subs
    assert backup.execute("SELECT * FROM notes ORDER BY id").fetchall() == original_notes
    backup.close()
    again = DuckDBStorage(legacy, shared=False)
    assert len(again.get_by_slug("legacy").revision_states) == 1
    again.close()


def test_disconnect_revokes_before_removing_account(owned, monkeypatch):
    service, accounts = owned
    vault = MagicMock()
    monkeypatch.setattr(service.leetcode, "_credential_vault", lambda account: vault)
    assert service.leetcode.disconnect()
    vault.revoke.assert_called_once()
    assert accounts.get_connection() is None
    assert service.storage.get_by_slug("shared") is not None
    assert not service.leetcode.validate_authenticated_credentials()


def test_review_state_survives_reopen_and_account_index_rebuild(owned):
    service, accounts = owned
    service.mark_reviewed("shared", "retained review")
    service.memory_index_all()
    accounts.save_connection(AccountConnection(username="bob"))
    service.memory_index_all()
    bob_ids = {key for key, value in service.memory_engine.index._index.items() if value.get("source_account") == "bob"}
    accounts.save_connection(AccountConnection(username="alice"))
    service.memory_index_all(force_rebuild=True)
    assert bob_ids <= service.memory_engine.index._index.keys()
    base, knowledge, db = service.base_dir, service.knowledge_dir, service._db_path
    service.close_storage()
    reopened = CodeMemoryService(base_dir=base, knowledge_dir=knowledge, db_path=db, account_service=accounts)
    try:
        assert reopened.get_problem_priority("shared").days_since_last_activity == 0
        assert reopened.get_problem("shared").notes[0].content == "retained review"
        accounts.save_connection(AccountConnection(username="bob"))
        assert reopened.get_problem_priority("shared").days_since_last_activity >= 30
        assert not reopened.get_problem("shared").notes
    finally:
        reopened.close_storage()


def test_failed_keyring_cleanup_cannot_revive_revoked_credentials(tmp_path, monkeypatch):
    from codememory.connectors.leetcode import vault as module
    entries = {}
    keyring = MagicMock()
    keyring.get_password.side_effect = lambda service, name: entries.get(name)
    keyring.set_password.side_effect = lambda service, name, value: entries.__setitem__(name, value)
    keyring.delete_password.side_effect = RuntimeError("keyring unavailable")
    monkeypatch.setattr(module, "keyring", keyring)
    path = str(tmp_path / "vault.json")
    vault = module.CredentialVault("alice", path)
    vault.store("synthetic-session-alice", "synthetic-csrf-alice")
    assert "synthetic-session-alice" not in str(entries)
    vault.revoke()
    assert module.CredentialVault("alice", path).retrieve() == (None, None)
    vault.store("synthetic-session-new", "synthetic-csrf-new")
    assert vault.retrieve() == ("synthetic-session-new", "synthetic-csrf-new")


def test_private_metadata_preserved_and_storage_checks_membership(owned):
    service, accounts = owned
    now = datetime.now(timezone.utc)
    raw = service.storage.get_by_slug("shared")
    raw.revision_states = [RevisionState(source_account=owner, last_activity_at=now,
        due_at=now + timedelta(days=days), priority_override=days, metadata={"private": owner})
        for owner, days in [("alice", 3), ("bob", 9)]]
    service.storage.save(raw)
    bob = raw.revision_states[1].model_dump()
    service.mark_reviewed("shared")
    alice = service.get_problem("shared").revision_states[0]
    assert alice.due_at == now + timedelta(days=3) and alice.priority_override == 3
    assert alice.metadata == {"private": "alice"}
    with pytest.raises(ValueError, match="Problem does not belong"):
        service.storage.save_private_state(service.storage.get_by_slug("bob-only"), "alice")
    accounts.save_connection(AccountConnection(username="bob"))
    assert service.get_problem("shared").revision_states[0].model_dump() == bob


def test_all_api_views_switch_scope_and_topics_filter_before_limit(owned):
    service, accounts = owned
    raw = service.storage.get_by_slug("bob-only")
    raw.topics = ["Bob exclusive topic"]
    service.storage.save(raw)
    with TestClient(create_app(service)) as client:
        for owner, expected in [("alice", 1), ("bob", 2), ("alice", 1)]:
            accounts.save_connection(AccountConnection(username=owner))
            assert client.get("/api/v1/problems").json()["total"] == expected
            assert client.get("/api/v1/submissions").json()["total"] == expected
            for path in ["dashboard", "analytics", "knowledge", "revision", "search?q=bob-only", "health"]:
                response = client.get(f"/api/v1/{path}")
                assert response.status_code == 200
                if owner == "alice" and not path.startswith("search?"):
                    assert "bob-only" not in response.text and "private-bob" not in response.text
                elif owner == "alice":
                    assert response.json()["results"] == []
            topics = client.get("/api/v1/revision/topics").json()
            assert ("Bob exclusive topic" in topics) == (owner == "bob")
        accounts.save_connection(AccountConnection(username="bob"))
        queue = client.get("/api/v1/revision?limit=1&topic=Bob%20exclusive").json()
        assert len(queue) == 1 and queue[0]["slug"] == "bob-only"


def test_concurrent_analytics_and_problem_reads_keep_result_sets_separate(owned):
    from concurrent.futures import ThreadPoolExecutor
    service, _ = owned
    with TestClient(create_app(service)) as client:
        paths = ["analytics", "dashboard", "problems", "revision", "submissions"] * 6
        with ThreadPoolExecutor(max_workers=5) as pool:
            responses = list(pool.map(lambda path: client.get(f"/api/v1/{path}"), paths))
        for response in responses:
            assert response.status_code == 200, response.text
            assert "bob-only" not in response.text and "private-bob" not in response.text
