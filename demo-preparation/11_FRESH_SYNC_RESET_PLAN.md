# Fresh LeetCode Sync Verification and Safe Reset Plan

## Decision

Do not delete rows from an existing database for the first verification. Run the authenticated sync against a brand-new, isolated CodeMemory data root. This gives a genuinely fresh history without touching the existing recording/runtime data, avoids ambiguous mixed-origin attempts, and can be rolled back by stopping the isolated API and returning to the prior configuration. Keep the new root for review; do not delete it automatically.

## Current baseline and path certainty

- The Git branch is `codex/demo-readiness`; the worktree already contains frontend changes, a staged generated TypeScript build-info file, `.venv-demo/`, and untracked demo documentation. Those are preserved.
- At inspection, no TCP listener was found on ports `3000`, `8000`, `8001`, or `8501`. The process listing found no `python`, `uvicorn`, or `node` process. A CIM process query was denied by Windows access controls. Therefore no currently running API database path can be confirmed; do not describe an existing file as the active database.
- API defaults in `src/api/config.py` are `CODEMEMORY_DATA_DIR=data`, `CODEMEMORY_KNOWLEDGE_DIR=knowledge`, `CODEMEMORY_DB_PATH=data/codememory.duckdb`, host `127.0.0.1`, port `8000`. The prior recording guide instead configures its isolated API to use `demo-preparation/recording-data/codememory-demo.duckdb` and `demo-preparation/recording-knowledge` on port `8001`.
- Existing candidate data roots were only inspected by path and file metadata, not opened: `demo-preparation/recording-data/` (DuckDB, `accounts/`, `parquet/`, `ai_analyses.parquet`, `memory_embeddings.parquet`) with `demo-preparation/recording-knowledge/`; and `demo-preparation/runtime-data/` (DuckDB plus a WAL and subdirectories) with `demo-preparation/runtime-knowledge/`. Leave all four roots untouched.
- The proposed fresh paths below did not exist at inspection:
  - `demo-preparation/fresh-sync-20261014-data/`
  - `demo-preparation/fresh-sync-20261014-knowledge/`
  - DuckDB: `demo-preparation/fresh-sync-20261014-data/codememory-demo.duckdb`
  - Account metadata: `demo-preparation/fresh-sync-20261014-data/accounts/account_connections.json`
  - Derived Parquet: `demo-preparation/fresh-sync-20261014-data/parquet/`
  - Other generated analysis/index files may be under the data root, including `ai_analyses.parquet` and `memory_embeddings.parquet`.
- Credential storage is not isolated by the API data-root variables. `CredentialVault` uses the fixed keyring service name `CodeMemory` with account-specific key names. Its fallback file is relative to the process working directory: `data/accounts/leetcode_vault_<account>.json`. The constructor reads or creates the keyring master key immediately. If key initialization fails, `store()` cannot encrypt and fails before its file fallback; that fallback only applies if encryption succeeded but storing the encrypted vault payload in keyring failed.
- The Settings component calls `validateLeetCodeCredentials()` on mount. The API then constructs a vault for the connected username, or `default` if none is connected, retrieves credentials, and may make a LeetCode validation request if credentials exist. Therefore opening Settings under the current Windows profile is not safe for this no-credential/no-network preparation: it could inspect an existing keyring entry and, if found, trigger network validation. No Settings page was opened, and no credential or keyring operation was performed here.

The existing data directories may contain user data or account-related files. No backup was created because the active root is unknown; copying all candidate roots would create unnecessary copies of data that may include credential material. Since this plan does not modify either existing root, no existing-data backup is required for the isolated run. If an in-place reset is later requested, first identify the active paths, stop the API, and back up those exact roots before approval or mutation.

## Why the supported disconnect controls are not a history reset

- Settings > LeetCode > **Disconnect** calls `DELETE /api/v1/leetcode/connect`. The service removes the LeetCode connection/sync metadata and explicitly preserves imported history. The UI confirmation also says previously imported history stays in the local index.
- Settings > LeetCode > **Revoke credentials** calls the auth revoke endpoint and removes stored credentials from the credential vault. It does not delete submissions or history.
- Neither control resets imported history. Do not click either as a substitute for a data reset.

The canonical database stores `problems`, `attempts`, `submissions`, and `notes`. `source_provider` and `source_account` identify a submission; attempts and notes do not have the same per-record source provenance. A problem/attempt may therefore mix imported submissions and manually created work. The standard composite delete removes a whole problem and updates filesystem/Parquet outputs; DuckDB's direct delete only deletes the problem row. Neither is a safe selective LeetCode-history reset. Other derived files include `parquet/problems.parquet`, `attempts.parquet`, `submissions.parquet`, `ai_analyses.parquet`, and `memory_embeddings.parquet`. A custom row delete would need to handle mixed attempts, notes, empty parent records, FS exports, Parquet snapshots, account metadata, analyses, and semantic indexes consistently. No supported selective-reset operation was found.

## Preconditions before the isolated verification

1. Resolve the known Python package blocker first: `tests/test_leetcode_authenticated.py` cannot collect because Polars startup raises `unknown feature flag: 'sse3'`. Do not weaken tests or change dependency versions blindly.
2. Confirm the Python environment in [02_RUN_AND_TEST_GUIDE.md](02_RUN_AND_TEST_GUIDE.md) is usable.
3. Obtain explicit approval before connecting a real account or triggering a network sync. Use a dedicated LeetCode test account with synthetic/non-sensitive history, not a personal or customer account. Never expose account identifiers or credentials in the recording.
4. Confirm the chosen data and knowledge paths are still absent. If either exists, stop and choose new paths; do not overwrite.
5. Confirm ports `8001` and `3000` are free. Stop any previous process that could use the same DB before startup. Never run two processes against one DuckDB file.

## Commands for a new isolated run

Run from the repository root in PowerShell after approval. These commands use a new isolated root and never point to the repository's `data/`, `knowledge/`, `recording-data/`, or `runtime-data/`.

### Terminal 1 — start the source API

```powershell
$repoRoot = (Resolve-Path .).Path
$demoData = Join-Path $PWD 'demo-preparation/fresh-sync-20261014-data'
$demoKnowledge = Join-Path $PWD 'demo-preparation/fresh-sync-20261014-knowledge'
$demoDb = Join-Path $demoData 'codememory-demo.duckdb'
$repoSrc = Join-Path $repoRoot 'src'
$demoPython = Join-Path $repoRoot '.venv-leetcode-locked\Scripts\python.exe'

if (Test-Path -LiteralPath $demoData) { throw "Data path already exists; choose a new isolated path." }
if (Test-Path -LiteralPath $demoKnowledge) { throw "Knowledge path already exists; choose a new isolated path." }
if (Get-NetTCPConnection -State Listen -LocalPort 8001 -ErrorAction SilentlyContinue) { throw "Port 8001 is occupied; identify and stop that service before continuing." }
New-Item -ItemType Directory -Path $demoData | Out-Null
Set-Location $demoData

$env:CODEMEMORY_DATA_DIR = $demoData
$env:CODEMEMORY_KNOWLEDGE_DIR = $demoKnowledge
$env:CODEMEMORY_DB_PATH = $demoDb
$env:CODEMEMORY_API_HOST = '127.0.0.1'
$env:CODEMEMORY_API_PORT = '8001'
$env:CODEMEMORY_LOG_LEVEL = 'INFO'
$env:CODEMEMORY_PROBLEM_SOURCE = 'local'
$env:AI_PROVIDER = 'heuristic'
$env:PYTHONPATH = $repoSrc
& $demoPython -m uvicorn api.app:create_app --factory --host 127.0.0.1 --port 8001
```

The API working directory is the new data root, so the vault's relative fallback path is confined to `$demoData\data\accounts\leetcode_vault_<account>.json`. The account metadata and DuckDB are directly under `$demoData`. Both paths remain within the isolated root.

Wait for the Uvicorn startup line in this terminal. In another PowerShell window, make the read-only health check:

```powershell
Invoke-RestMethod 'http://127.0.0.1:8001/api/v1/health'
```

Confirm the response is healthy before proceeding. Keep the terminal open and note that this process was started with `fresh-sync-20261014-data/codememory-demo.duckdb` and `fresh-sync-20261014-knowledge`. Do not print environment variables during recording.

### Terminal 2 — start the frontend

```powershell
Set-Location .\frontend
if (Get-NetTCPConnection -State Listen -LocalPort 3000 -ErrorAction SilentlyContinue) { throw "Port 3000 is occupied; identify and stop that service before continuing." }
$env:NEXT_PUBLIC_API_URL = 'http://127.0.0.1:8001/api/v1'
npm run dev -- --hostname 127.0.0.1 --port 3000
```

For a no-product-code-change test, use a separately provisioned Windows user profile with its own Credential Manager and a dedicated synthetic LeetCode account. Start the API with its current working directory inside the fresh root so any encrypted file fallback resolves under that root (for example, `<fresh-root>\data\accounts\...`); continue to set `CODEMEMORY_DATA_DIR` and `CODEMEMORY_DB_PATH` to that same isolated `data` directory. Do not start this in the existing Windows profile: the Settings page's initial validation uses the `default` account keyring namespace before a new user is connected. In the new profile, verify the Credential Manager backend is usable without listing or reading any existing items. If it is unavailable, stop; credential storage may fail before the file fallback can be used.

The current code does not expose a configurable keyring service namespace. If a separate Windows profile is not practical, the smallest code-level isolation proposal is to make the keyring service name and vault-file directory injectable/configurable (keeping current defaults unchanged), then set a unique demo-only namespace and an absolute vault path under the fresh data root. Thread the configuration through `CredentialVault` and the LeetCode service/API construction. This is a proposal only; no code was changed for it. After isolation is in place, opening Settings may safely perform its initial no-credential check, and credential entry/sync still require approval. Never test the existing profile by retrieving or printing its credentials.

Only after the credential-storage path is resolved and the user approves an external request, click the supported **Sync full history** control once. This triggers a real external request and is intentionally excluded from this preparation run. Confirm completion in the on-screen sync summary and via the API using the account's normal authenticated UI flow. Check the Find Peak Element submission metric displays approximately `44.19 MB` when the approved test account contains that known matching submission. Do not claim the raw GraphQL unit is formally established by this check.

### Stop and rollback

Stop frontend Terminal 2 with `Ctrl+C`, then API Terminal 1 with `Ctrl+C`. Wait for both processes to exit cleanly. The old candidate roots remain untouched. Roll back simply by not using the new root and restoring the prior API environment/configuration; retain the new root for review. No cleanup/deletion is part of this procedure.

## In-place reset status

An in-place deletion/reset is **not prepared for execution** because the active database path is unknown and the repository has no safe selective LeetCode-history reset route. Before preparing one, the API must be started or its actual process command line/configuration must be supplied, and the exact database, knowledge, account metadata, and derived-index paths must be identified. Then provide a backup manifest and a dry-run record count grouped by `source_provider` and `source_account` without exposing code or credentials. Obtain fresh approval for the exact paths and row classes before any mutation.

## Present verification blockers

- No API/frontend service was running on the inspected standard ports. The active DB path cannot be confirmed.
- The authenticated sync integration tests are blocked at collection by the installed Polars package's CPU-flag parsing error.
- Settings auto-validates credentials on mount using the current account namespace (`default` before account connection), potentially reading a vault and making a validation request. A sync is not cleared to run under the existing Windows profile. Credential-storage isolation must be established first; the earlier keyring access issue remains unresolved.
- This preparation did not open account storage, access credentials, use the network, run a sync, or inspect/modify database records.
