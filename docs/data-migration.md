# Account ownership and Windows data migration

## Ownership before and after

Before migration, submissions already carried `source_provider` and
`source_account`, but attempts/notes and the mutable problem timestamp were
shared. A review of a problem by A could affect B's notes and revision priority.

After migration:

| Entity | Ownership |
| --- | --- |
| Problem definition | Shared title, slug, difficulty, statement and topics |
| Historical submission | Existing provider/account provenance; unchanged |
| Attempt reasoning, mistakes and analysis | Explicit `source_account` |
| Note | Explicit `source_account` |
| Revision state | `(problem_id, account_key)` in `account_problem_state` |
| Memory documents/vectors | Account provenance and account-prefixed identity |

Revision state preserves last activity/review time, optional priority/due fields
and arbitrary metadata. Current priority/due behavior remains calculated from
scoped history; the UI has no persistent snooze or manual priority editor.
Private saves change only owned notes and revision rows, without rewriting
historical submissions. Queries project the active account before deriving
analytics, search, semantic results, knowledge or revision scores. API requests
capture account context for their lifetime. This is local account isolation,
not an internet-facing authentication or multi-user authorization server.

## Deterministic legacy attribution

The idempotent `account_ownership_v1` migration assigns an attempt based on its
submission owners. A note linked to an attempt uses that attempt's submission
owners; a problem-level note uses the problem's owners. A single known owner
receives the record. Manual records without external provenance remain local.
Mixed/unknown external ownership is kept under
`__codememory_legacy_unassigned__`, excluded from account-private views. No record
is deleted or copied into every account. Ambiguous attribution requires a later
explicit recovery decision; there is no automatic reassignment on switching.

Before changing an existing database, CodeMemory checkpoints and closes it,
makes a hash-verified `<database>.pre-ownership-v1.bak`, then performs additive
schema/backfill changes in a transaction. Submissions are never updated or
deleted by that migration. Filesystem/Parquet serializers retain ownership.

## Windows paths and copy migration

Installed/frozen runtime defaults to `%LOCALAPPDATA%\CodeMemory\`, containing:

```text
codememory.duckdb
accounts/                  connection metadata, encrypted vault files
settings.json              user preferences
knowledge/                 Markdown exports
parquet/ and caches        derived indexes
logs/sidecar.log
runtime-migration.json
ownership-verification.json  produced by the explicit migration script
```

Actual existing filenames are retained during copy. `CODEMEMORY_APP_DIR`
overrides the desktop root. `CODEMEMORY_DATA_DIR`, `CODEMEMORY_DB_PATH` and
`CODEMEMORY_KNOWLEDGE_DIR` remain authoritative overrides and disable automatic
copy migration. `CODEMEMORY_DESKTOP=1` enables desktop path behavior outside a
frozen build. `CODEMEMORY_LEGACY_DIR` identifies a legacy root containing `data/`
and `knowledge/`. Automatic discovery checks the launch/installation location;
it does not scan arbitrary drives or merge multiple databases.

Close all CodeMemory/backend processes before explicit migration:

```powershell
.venv/Scripts/python.exe scripts/migrate_runtime.py --source . --check-only
.venv/Scripts/python.exe scripts/migrate_runtime.py --source .
```

Files are copied to a separate staging directory, verified by SHA-256, then
published as the runtime root. The original is retained. A changing/locked
source fails safely; distinct nonempty stores are not merged. Existing target
databases are used without overwriting them. Other legacy locations require
an explicit `--source`; they are not silently combined.

On this workspace the verified migration preserved all original columns of
**79 problems, 174 attempts, 111 submissions and 0 canonical notes**. Source
`data/` and `knowledge/` remain. `frontend/data/` and other legacy stores were not
modified/deleted. See the destination's `ownership-verification.json`.

## Recovery

Schema downgrade is not automatic: restoring an old schema after new writes
would lose those new writes. With the application stopped, first copy the
entire current runtime folder to a new recovery location. Restore the
pre-ownership database backup into another separate recovery directory and
configure an earlier application to use that directory, or point it at the
retained original store. Keep the current store for reconciliation of later
notes/reviews/submissions. Never overwrite the only current copy.

OS keyring secrets belong to the Windows user. Copying encrypted files alone
to another Windows account may require reconnecting credentials. Disconnect
writes a persistent revocation marker before attempting keyring/file cleanup,
so a failed cleanup cannot revive a revoked session. Revoke keeps the public
connection; switching preserves separate account vaults; reconnect after
disconnect requires newly stored credentials.
