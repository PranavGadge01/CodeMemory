# LeetCode Integration Guide

## Overview

CodeMemory's LeetCode integration has two complementary paths:

1. **Account sync** — a live, read-only connection to LeetCode's *public* GraphQL
   API that syncs your public profile and your most recent accepted submissions.
   No password, session cookie, or token is ever requested or stored.
2. **Dataset import** — the import-first fallback that ingests a LeetCode export
   file (JSON/CSV), including source code, runtime and memory.

```
Account sync (public GraphQL)          Dataset import (export file)
        ↓                                       ↓
LeetCodeAccountService                 LeetCodeParser (JSON / CSV)
        ↓                                       ↓
LeetCodeSyncEngine                     LeetCodeMapper (Normalization)
        ↓                                       ↓
LeetCodeMapper (Normalization)         LeetCodeImporter (Validation + Dedup)
        ↓                                       ↓
CodeMemory Core (ImportService) ← both paths converge here
        ↓
CompositeStorage (DuckDB + Parquet + Markdown)
        ↓
Analytics / Search / Patterns / Revision / UI
```

Both the UI and the CLI reach the account lifecycle exclusively through the
canonical service surface `service.leetcode`:

```python
service.leetcode.connect(username)   # validate + store account metadata
service.leetcode.sync(limit=None)    # one sync run, returns a SyncStatus
service.leetcode.status()            # LeetCodeAccountStatus for display
service.leetcode.disconnect()        # drop account state, keep history
```

An optional timer can drive that same `sync()` call in the background, through
`service.autosync` (see [Automatic background sync](#automatic-background-sync)).

Neither the Streamlit pages nor the CLI construct the sync engine or the GraphQL
client directly.

---

## Account Sync — what it actually does

### What is synchronized

| Data | Available | Notes |
|------|-----------|-------|
| Public profile | ✅ | username, display name, avatar, ranking |
| Solving progress | ✅ | total solved by difficulty (Easy/Medium/Hard) |
| Recent accepted submissions | ✅ | title, slug, language, timestamp, status |
| Source code | ❌ | not exposed by the public API for recent submissions |
| Runtime / memory | ❌ | not exposed by the public API for recent submissions |
| Full submission history | ❌ | only a server-bounded recent window is served |

### The coverage contract (important)

The public `recentAcSubmissionList` query returns only the most recent **accepted**
submissions — a server-bounded window with **no paging cursor**. CodeMemory
therefore:

- always reports `coverage = "recent-window"`, and never claims a complete history;
- persists records exactly as the API describes them — **empty code, null runtime
  and null memory** rather than fabricated stand-ins (a placeholder snippet would
  corrupt the canonical submission hash and misrepresent your history);
- keeps a purely **local** watermark of the newest persisted submission. The
  watermark is never sent to LeetCode as a `since`/`after` parameter — the public
  API has no such parameter;
- detects **gaps**: when the oldest submission in the current window is newer than
  the newest persisted one, submissions exist on LeetCode that fell outside the
  window between two syncs. These are reported (`gap_detected`) but **cannot be
  recovered by re-syncing** — import an export file for the missing range.

Sync states are reported honestly: `Success` only when every discovered record was
persisted and the profile fetch succeeded, `Partial` when a record or the profile
fetch failed, and `Failed` when the run could not complete. A failed validation
never leaves a connected account behind, and the watermark only advances after
records are durably persisted.

Sync is **idempotent**: re-syncing the same window adds nothing. Deduplication
uses the external submission id (`leetcode_<id>`) as the primary key and a
deterministic SHA-256 fingerprint as the fallback (see "Deduplication Strategy").

---

## CLI Commands

### Account sync

```bash
# Connect a LeetCode account (validates the public profile; no credentials)
python -m codememory.cli.main leetcode connect <username>

# Run one sync of the public profile + recent submission window
python -m codememory.cli.main leetcode sync
python -m codememory.cli.main leetcode sync --limit 10   # cap the window request

# Show account + sync status (connection, counts, coverage, gap, blind spots)
python -m codememory.cli.main leetcode status

# Disconnect (removes account/sync state only; imported history is preserved)
python -m codememory.cli.main leetcode disconnect
```

### Automatic background sync

The CLI configures the scheduler's persisted preference; the running web app
picks it up on its next start (a CLI process exits, so it does not run the worker
itself):

```bash
# Turn automatic sync on, every 15 minutes (clamped to 5 min – 24 h)
python -m codememory.cli.main leetcode autosync enable --interval 900

# Use the default interval of one hour
python -m codememory.cli.main leetcode autosync enable

# Turn it off
python -m codememory.cli.main leetcode autosync disable

# Show the configuration and whether the app's worker is running
python -m codememory.cli.main leetcode autosync status
```

`enable` and `disable` exit `0`; an unrecognised subcommand exits `1`.


Exit codes for scripting:

| Command / outcome | Exit code |
|-------------------|----------|
| `connect` succeeded | `0` |
| `connect` failed (validation, transport, missing username) | `1` |
| `sync` succeeded | `0` |
| `sync` completed partially (`Partial`) | `2` |
| `sync` failed or no account connected | `1` |
| `status` with a connected account | `0` |
| `status` with no connected account | `1` |
| `disconnect` (connected or not — idempotent) | `0` |

Error messages printed by these commands are scrubbed: they never contain
credentials, cookies, authorization headers or request bodies.

### Dataset import (fallback with code + metrics)

```bash
# Validate a LeetCode dataset file (no data stored)
python -m codememory.cli.main leetcode validate path/to/data.json

# Preview import statistics without committing
python -m codememory.cli.main leetcode preview path/to/data.json

# Import LeetCode dataset idempotently
python -m codememory.cli.main leetcode import path/to/data.json

# CSV files are also supported
python -m codememory.cli.main leetcode import path/to/data.csv
```

---

## UI

### Account connection (Settings)

Open **Settings → LeetCode Account Connection**:

1. Enter your **public LeetCode username** — nothing else is requested or accepted.
2. Click **Connect Account**; the profile is validated against the public API and
   a validation failure is shown as an error (never as a connected state).
3. The connected card shows the sync state, last attempted and last successful
   sync, imported/skipped/failed counts, and solved-by-difficulty progress.
4. **Sync coverage & window** states the coverage contract: window limit, records
   in window, truncation, gap detection and the fields the public API cannot
   supply.
5. **Sync Now** runs one sync and reports `Success`, `Partial` or `Failed`
   distinctly — a partial run is never displayed as success. It goes through the
   scheduler's lock (see [Automatic background sync](#automatic-background-sync)),
   so it cannot overlap a scheduled sync.
6. **Disconnect Account** removes the connection and sync state and tells you
   your imported history has been preserved.

A gap is always accompanied by an honest explanation: the missing submissions
exist on LeetCode but are unreachable through the public recent-submission
window, and re-syncing will not fetch them.

### Automatic background sync

**Settings → LeetCode Account Connection → Automatic background sync** lets the
app sync on a timer instead of on demand. It is **off by default** and stays off
until you turn it on; a process that never opts in never starts the worker.

```python
service.autosync.ensure_running()          # start it if it is enabled (idempotent)
service.autosync.set_enabled(True)         # turn it on and start the worker
service.autosync.set_interval(900)         # seconds; clamped to 5 min – 24 h
service.autosync.sync_now()                # one manual sync through the same lock
service.autosync.status()                  # enabled / interval / running / next run
```

What it does — and just as importantly, what it does not:

- **It runs the same sync as Sync Now.** The scheduler adds no sync logic of its
  own: it calls `service.leetcode.sync()` on a `CodeMemoryService` of its own and
  reaches nothing else. No transport, no retry policy, no pagination, no
  watermark handling — those stay in the sync engine.
- **It syncs on its own DuckDB connection.** A single DuckDB connection is not
  safe for concurrent use from two threads, so the worker builds its service with
  `shared_duckdb_connection=False`. Two connections to the same file are
  serialised by DuckDB itself, so a background sync never blocks the UI thread.
- **It never overlaps itself or a manual sync.** One non-reentrant lock covers
  both the scheduled ticks and `sync_now`, and it is released on `Success`,
  `Partial`, `Failed` and on any exception. If a manual sync is in flight when a
  tick is due, the tick is skipped rather than queued; if you click **Sync Now**
  while one is running, you are told so instead of waiting.
- **No account, no traffic.** Every tick first checks the local connection store.
  With no connected account the tick does nothing — no request, no database
  connection. Disconnecting therefore stops the scheduled traffic without
  silently rewriting your preference.
- **A failing tick does not stop the scheduler.** The outcome is logged and the
  next interval gets another chance. Errors surfaced through `status()` are
  scrubbed, like every other message in this integration.
- **One worker, ever.** `start()` is idempotent and the scheduler is a lazy
  per-service singleton, so repeated Streamlit reruns cannot stack or duplicate
  workers. The worker is a daemon thread and stops when the service is retired —
  notably by **Clear All Data**, which also deletes the preference file.

The preference (`enabled`, `interval`) is stored as plain JSON at
`data/leetcode_autosync.json`, written atomically; a missing or unreadable file
always falls back to *disabled*. The interval is clamped between 5 minutes and
24 hours to stay polite toward the unauthenticated endpoint.

### Dataset import

Navigate to **Data Import**:

1. Select **"LeetCode Export Dataset (JSON / CSV)"** as source type
2. Upload your LeetCode JSON or CSV file
3. Review the validation preview (problems, submissions, duplicates, errors)
4. Click **"Confirm & Import LeetCode Dataset"**

---

## Supported Input Formats

### JSON Format (Recommended)

Arrays of submission objects exported from LeetCode or tools that generate LeetCode-compatible JSON:

```json
[
  {
    "submission_id": "1003",
    "title": "Two Sum",
    "title_slug": "two-sum",
    "difficulty": "Easy",
    "topics": ["Array", "Hash Table"],
    "language": "python3",
    "status": "Accepted",
    "runtime": "45 ms",
    "memory": "17.2 MB",
    "timestamp": 1700007200,
    "url": "https://leetcode.com/problems/two-sum/",
    "code": "class Solution:\n    def twoSum(self, nums, target):\n        seen = {}\n        for i, n in enumerate(nums):\n            diff = target - n\n            if diff in seen:\n                return [seen[diff], i]\n            seen[n] = i"
  },
  {
    "submission_id": "1002",
    "title": "Two Sum",
    "title_slug": "two-sum",
    "difficulty": "Easy",
    "topics": ["Array", "Hash Table"],
    "language": "python3",
    "status": "Time Limit Exceeded",
    "timestamp": 1700003600,
    "code": "class Solution:\n    def twoSum(self, nums, target):\n        for i in range(len(nums)):\n            for j in range(len(nums)):\n                if i != j and nums[i] + nums[j] == target:\n                    return [i, j]"
  }
]
```

### CSV Format

CSV with header row. Recognized column names:

| Column Name    | Aliases                                                | Notes                              |
|----------------|--------------------------------------------------------|------------------------------------|
| `title`        | `Problem Title`, `problem_title`, `Question Title`     | Required                           |
| `language`     | `lang`, `Language`                                     | Required                           |
| `status`       | `Status`, `Result`, `status_display`                   | Required                           |
| `code`         | `source_code`, `Code`, `Source Code`                   | Optional but recommended           |
| `submission_id`| `id`, `Submission ID`                                  | Optional                           |
| `difficulty`   | `Difficulty`, `Level`                                  | Optional                           |
| `topics`       | `Topics`, `tags`, `Tags`, `topic_tags`                 | Comma-separated string or list     |
| `runtime`      | `Runtime`, `Execution Time`                            | e.g. `"45 ms"`                     |
| `memory`       | `Memory`, `Memory Usage`                               | e.g. `"17.2 MB"`                   |
| `timestamp`    | `Date`, `submitted_at`, `created_at`                   | Epoch seconds, ISO string, or int  |

---

## Status Normalization

LeetCode raw status strings are normalized to CodeMemory `SubmissionStatus` enum values:

| LeetCode Status        | Aliases              | CodeMemory Value          |
|------------------------|----------------------|---------------------------|
| `Accepted`             | `ac`, `10`           | `ACCEPTED`                |
| `Wrong Answer`         | `wa`, `11`           | `WRONG_ANSWER`            |
| `Time Limit Exceeded`  | `tle`, `12`          | `TIME_LIMIT_EXCEEDED`     |
| `Memory Limit Exceeded`| `mle`, `13`          | `MEMORY_LIMIT_EXCEEDED`   |
| `Runtime Error`        | `re`, `14`           | `RUNTIME_ERROR`           |
| `Compile Error`        | `ce`, `15`           | `COMPILE_ERROR`           |

---

## Language Normalization

| LeetCode Value | Normalized Value |
|----------------|-----------------|
| `python3`      | `Python`        |
| `python`       | `Python`        |
| `cpp`          | `C++`           |
| `java`         | `Java`          |
| `golang`       | `Go`            |
| `javascript`   | `JavaScript`    |
| `typescript`   | `TypeScript`    |
| `rust`         | `Rust`          |
| `csharp`       | `C#`            |
| `kotlin`       | `Kotlin`        |
| `swift`        | `Swift`         |
| `ruby`         | `Ruby`          |

---

## Timestamp Parsing

Timestamps are parsed in the following priority order:

1. **Epoch seconds** (e.g. `1700007200`) — automatically detected if value > 0 and < `1e11`
2. **Epoch milliseconds** (e.g. `1700007200000`) — detected if value > `1e11`, divided by 1000
3. **ISO 8601 string** (e.g. `"2026-09-06T10:00:00Z"` or `"2026-09-06T10:00:00+05:30"`)
4. **Common date strings** (`"2026-09-06 10:00:00"`, `"2026-09-06"`)
5. **Fallback**: current UTC timestamp

All timestamps are stored in UTC internally.

---

## Deduplication Strategy

CodeMemory uses a **two-tier deduplication system** to ensure the same submission is never imported twice.

### Tier 1: External Submission ID (Primary)
If `submission_id` is available, it is prefixed with `"leetcode_"` and used as the canonical ID:
```
external_id = "leetcode_<submission_id>"
```
Example: `"leetcode_1003"`

### Tier 2: Deterministic SHA-256 Hash (Fallback)
If no `submission_id` is present, a deterministic fingerprint hash is computed:
```python
fingerprint = f"{problem_slug}:{timestamp}:{language}:{status}:{code.strip()}"
hash = SHA256(fingerprint)
```

This hash is stored in `submission_hash` on the `Submission` domain model and checked before every import.

### Behavior

| Import              | Expected Result                          |
|---------------------|------------------------------------------|
| First import        | All records imported                     |
| Same dataset again  | 0 new records (all duplicates detected)  |
| New submissions added | Only net-new submissions imported      |

---

## Incremental Import

CodeMemory fully supports incremental imports from growing LeetCode datasets.

**Example workflow:**

```bash
# Day 1: 100 submissions
python -m codememory.cli.main leetcode import day1_data.json
# → Imported: 100 submissions

# Day 2: 110 submissions (10 new)
python -m codememory.cli.main leetcode import day2_data.json
# → Imported: 10 submissions (100 duplicates skipped)
```

Import statistics reported:
- `total_read`: total records in file
- `valid_count`: records passing schema validation
- `imported_count`: net-new records stored
- `duplicate_count`: records already in storage (skipped)
- `error_count`: records failing validation
- `imported_problems`: list of affected problem slugs

---

## Knowledge File Generation

After import, CodeMemory automatically generates or updates Markdown knowledge files for each imported problem:

```
knowledge/
    two-sum/
        problem.md        ← Problem metadata and description
        attempts.md       ← Chronological attempt history
        metadata.json     ← Machine-readable metadata
        solution.py       ← Latest accepted solution source
```

### Preservation Guarantee
Importing new submissions for an existing problem **never overwrites** previous attempt history. All attempts are preserved in chronological order in `attempts.md`.

---

## CLI Commands (dataset import)

See the "CLI Commands" section above — account sync commands live there, and the
import/preview/validate commands are repeated here for convenience:

```bash
# Validate a LeetCode dataset file (no data stored)
python -m codememory.cli.main leetcode validate path/to/data.json

# Preview import statistics without committing
python -m codememory.cli.main leetcode preview path/to/data.json

# Import LeetCode dataset idempotently
python -m codememory.cli.main leetcode import path/to/data.json

# CSV files are also supported
python -m codememory.cli.main leetcode import path/to/data.csv
```

---

## UI Import

See "UI" above for the account-connection flow. For dataset import, open the
Streamlit application and navigate to **Data Import**:

1. Select **"LeetCode Export Dataset (JSON / CSV)"** as source type
2. Upload your LeetCode JSON or CSV file
3. Review the validation preview (problems, submissions, duplicates, errors)
4. Click **"Confirm & Import LeetCode Dataset"**

---

## Privacy & Security

CodeMemory is **local-first** by design. The account sync talks only to LeetCode's
**public, unauthenticated** GraphQL endpoint, and CodeMemory stores **zero** of the
following:

- LeetCode passwords
- Session cookies (`LEETCODE_SESSION`)
- Authentication tokens / API credentials
- Browser session data

The only data written for a connected account is non-sensitive public identity and
profile metadata (username, display name, avatar URL, ranking, solved counts) plus
local sync bookkeeping.

Errors surfaced to the UI and CLI are scrubbed before display: credentials,
cookies, authorization headers and raw request bodies are destroyed, and long
messages are truncated so a stack trace can never reach a user.

All data stays in your local `data/` directory.

---

## Known Limitations

1. **Sync is not a complete history**: the public API serves only a server-bounded
   window of recent accepted submissions, with no paging cursor. `coverage` is
   always `recent-window`. Older submissions must come from a dataset import.
2. **No code, runtime or memory from sync**: the public recent-submission query
   exposes none of them, so synced submissions carry empty code and null metrics.
   They are never fabricated. Import an export file when you need them.
3. **Detected gaps are not recoverable by syncing**: if the window moves past the
   local watermark, the missing submissions are reported but cannot be fetched.
4. **Automatic sync is bounded by the same window**: a scheduled sync is exactly
   the same public-API run as a manual one, so it can never recover a gap or
   fetch older submissions — and it cannot sync at all while no account is
   connected.
5. **No problem statement import**: LeetCode problem statements are copyrighted and
   are not parsed from exported data. The `problem.md` description field will be
   empty unless you manually add it.
6. **Code availability (import)**: submitted code is only included if your export
   tool captures it. Many LeetCode export tools capture only metadata.
7. **CSV encoding**: CSV files must be UTF-8 encoded.
8. **Auto-sync preference is per installation**: the preference lives in
   `data/leetcode_autosync.json`, so "Clear All Data" removes it along with
   everything else, and a running app does not pick up a preference changed from
   the CLI until it restarts.

---

## Architecture

The live integration is layered so that LeetCode-specific response shapes never
reach the domain layer, and no UI or CLI component touches the transport client:

```
LeetCodeClient (public GraphQL, typed errors, bounded retries)
        ↓
LeetCodeSyncEngine (Phase B contract: window, watermark, gap, dedup)
        ↓
LeetCodeAccountService (connect / sync / status / disconnect, error scrubbing)
        ↓
CodeMemoryService.leetcode  ← the only surface UI and CLI use
        ↓
ImportService → CompositeStorage → Analytics / Search / Patterns / Revision
```

Phase E adds one component beside that chain, and it adds *no* logic of its own —
it only times the canonical call:

```
LeetCodeSyncScheduler (Phase E: enable/disable, interval, one worker thread)
        │  calls service.leetcode.sync() and nothing else
        ↓
a CodeMemoryService of its own, built with shared_duckdb_connection=False
```

The scheduler owns no retry, backoff, timeout or pagination: a failing tick is
logged and the next interval tries again, so transport hardening stays exactly
where it already was.

The transport client class in `src/codememory/connectors/leetcode/client.py`
implements the GraphQL interface:

```python
class LeetCodeClient:
    def execute_query(self, query: str, variables: dict) -> dict | None: ...
    def fetch_user_profile(self, username: str) -> dict | None: ...
    def fetch_user_submissions(self, username: str, limit: int) -> list[LeetCodeSubmissionRaw]: ...
    def fetch_problem_details(self, problem_slug: str) -> LeetCodeProblemRaw | None: ...
```

Every request is bounded by explicit connect/read timeouts, and only transient
failures (network, timeout, 5xx, rate limiting) are retried, with bounded
exponential backoff and jitter. Permanent failures (4xx, malformed bodies, GraphQL
rejections) fail fast.

---

## Testing

Run the full test suite including LeetCode integration tests:

```bash
python -m pytest -v
```

No test in the normal suite reaches the live LeetCode network; every response and
fault is injected through the client's `opener` seam or a stubbed service surface.
Live integration tests are marked `live` and excluded from the default selection
(run explicitly with `pytest -m live`).

Key test files:
- `tests/test_leetcode_cli.py`: CLI connect/sync/status/disconnect, exit codes, secret scrubbing
- `tests/test_leetcode_ui.py`: Settings page driven through Streamlit's `AppTest` runner
- `tests/test_leetcode_autosync_phase_e.py`: the background scheduler — lifecycle, the shared
  sync lock, failure recovery, Settings and CLI integration. No test sleeps or reaches the
  network: intervals are injected through the scheduler's `wait_fn` seam.
- `tests/test_leetcode_service_phase_c.py`: the account/sync service surface
- `tests/test_leetcode_sync_phase_b.py`: the sync contract (window, watermark, gap, coverage)
- `tests/test_leetcode_client_network.py`: transport hardening (timeouts, retries, rate limits)
- `tests/test_leetcode_connector.py`: parser, mapper, connector unit tests
- `tests/test_leetcode_import.py`: end-to-end import, deduplication, incremental import
- `tests/fixtures/leetcode/sample_leetcode.json`: realistic JSON fixture (3 problems, 6 submissions)
- `tests/fixtures/leetcode/sample_leetcode.csv`: CSV fixture (2 problems, 2 submissions)
