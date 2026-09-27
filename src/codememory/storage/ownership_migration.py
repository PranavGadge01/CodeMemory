"""Additive ownership migration. No historical submission writes or deletes."""
import hashlib
import json
import shutil
from pathlib import Path
from codememory.domain.ownership import UNASSIGNED

VERSION = "account_ownership_v1"


def applied(conn):
    exists = conn.execute("SELECT count(*) FROM information_schema.tables WHERE table_name='schema_migrations'").fetchone()[0]
    return bool(exists and conn.execute("SELECT count(*) FROM schema_migrations WHERE version=?", [VERSION]).fetchone()[0])


def backup_before_open(db_path):
    """Checkpoint and close before copying: Windows locks an open DuckDB file."""
    source = Path(db_path)
    if str(db_path) == ":memory:" or not source.exists():
        return
    import duckdb
    conn = duckdb.connect(str(source))
    try:
        if applied(conn):
            return
        conn.execute("CHECKPOINT")
    finally:
        conn.close()
    backup = source.with_name(source.name + ".pre-ownership-v1.bak")
    if not backup.exists():
        shutil.copy2(source, backup)
        if hashlib.sha256(source.read_bytes()).digest() != hashlib.sha256(backup.read_bytes()).digest():
            raise RuntimeError("Ownership backup verification failed; database was not migrated")


def migrate_ownership(conn, db_path):
    if applied(conn):
        return
    conn.execute("BEGIN TRANSACTION")
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations(version VARCHAR PRIMARY KEY, applied_at TIMESTAMP DEFAULT current_timestamp)")
        conn.execute("ALTER TABLE attempts ADD COLUMN IF NOT EXISTS source_account VARCHAR")
        conn.execute("ALTER TABLE attempts ADD COLUMN IF NOT EXISTS mistakes_json VARCHAR")
        conn.execute("ALTER TABLE attempts ADD COLUMN IF NOT EXISTS analysis_json VARCHAR")
        conn.execute("ALTER TABLE notes ADD COLUMN IF NOT EXISTS source_account VARCHAR")
        conn.execute("""CREATE TABLE IF NOT EXISTS account_problem_state (
            problem_id VARCHAR, account_key VARCHAR, state_json VARCHAR NOT NULL,
            PRIMARY KEY(problem_id, account_key))""")
        # Freeze attribution once, based on the entire pre-migration history.
        for pid, updated in conn.execute("SELECT id, updated_at FROM problems").fetchall():
            subs = conn.execute("SELECT attempt_id, source_account, source_provider FROM submissions WHERE problem_id=?", [pid]).fetchall()
            def owner(rows):
                owners = {r[1] for r in rows}
                if len(owners) == 1 and (None not in owners or all(r[2] is None for r in rows)):
                    return next(iter(owners))
                return UNASSIGNED if rows else None
            problem_owner = owner(subs)
            for (aid,) in conn.execute("SELECT id FROM attempts WHERE problem_id=?", [pid]).fetchall():
                rows = [r for r in subs if r[0] == aid]
                att_owner = owner(rows) if rows else problem_owner
                conn.execute("UPDATE attempts SET source_account=? WHERE id=? AND source_account IS NULL", [att_owner, aid])
            for nid, aid in conn.execute("SELECT id, attempt_id FROM notes WHERE problem_id=?", [pid]).fetchall():
                note_owner = owner([r for r in subs if r[0] == aid]) if aid else problem_owner
                conn.execute("UPDATE notes SET source_account=? WHERE id=? AND source_account IS NULL", [note_owner, nid])
            state = {"source_account": problem_owner, "last_activity_at": updated.isoformat(),
                     "metadata": {"migration": VERSION, "legacy_problem_updated_at": updated.isoformat()}}
            conn.execute("INSERT INTO account_problem_state VALUES (?, ?, ?) ON CONFLICT DO NOTHING",
                         [pid, problem_owner or "", json.dumps(state)])
        conn.execute("INSERT INTO schema_migrations(version) VALUES (?)", [VERSION])
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
