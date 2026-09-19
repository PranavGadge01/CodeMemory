You are now responsible for making the ENTIRE LEETCODE INTEGRATION of CodeMemory production-grade.

IMPORTANT:
This is a focused workstream. Do NOT work on unrelated CodeMemory issues such as:
- AI provider integration
- embedding/hash stability
- general analytics redesign
- general UI redesign
- seed command
- unrelated storage bugs
- performance work outside the LeetCode pipeline

However, you MUST modify any LeetCode-related downstream code necessary to make the complete integration reliable.

==================================================
PROJECT CONTEXT
==================================================

CodeMemory is a personal coding-intelligence system that imports a developer's LeetCode/problem-solving history and turns it into:

LeetCode data
    ↓
Connector / Importer
    ↓
Domain models
    ↓
Storage
    ↓
Analytics / Patterns / Revision
    ↓
Memory / Search
    ↓
Knowledge Graph
    ↓
Ask CodeMemory

Relevant architecture:

src/codememory/connectors/
    base.py
    account/
    leetcode/

src/codememory/connectors/leetcode/
    capabilities.py
    client.py
    importer.py
    leetcode_connector.py
    mapper.py
    models.py
    parser.py
    sync.py

src/codememory/ingestion/
src/codememory/domain/
src/codememory/storage/
src/codememory/core/
src/codememory/app/

The existing audit identified the following known LeetCode issue:

B4:
LeetCodeConnector.fetch_user_submissions() fails on non-empty data because:
- leetcode_connector.py reads norm_rec.runtime / norm_rec.memory
- NormalizedSubmissionRecord defines runtime_ms / memory_mb
- timestamp typing is also inconsistent

The existing tests only exercise the EMPTY result path, so this bug escaped the suite.

There is also a broader Phase 8 requirement around:
- account architecture
- profile/progress synchronization
- initial sync
- incremental sync
- deduplication
- sync status
- disconnect
- settings/dashboard integration
- downstream updates

There is an explicit security constraint:
DO NOT introduce:
- passwords
- LeetCode cookies
- browser scraping
- unofficial/private APIs
- credential harvesting

Preserve manual import as a fallback.

==================================================
PHASE 1 — UNDERSTAND THE CURRENT IMPLEMENTATION
==================================================

Before modifying anything, inspect the complete LeetCode-related implementation.

Read:

- connectors/base.py
- connectors/account/*
- connectors/leetcode/*
- domain/models.py
- domain/import_schema.py
- domain/enums.py
- ingestion/importer.py
- ingestion/parsers.py
- storage/base.py
- storage/composite_repository.py
- storage/duckdb_repository.py
- core/service.py
- relevant Streamlit pages
- relevant CLI commands
- ALL existing LeetCode/account/sync tests
- docs/leetcode-integration.md
- docs/data_flow.md
- docs/data-model.md
- README sections describing LeetCode

Search the entire repository for:

- LeetCode
- leetcode
- sync
- account
- fetch_user_submissions
- submissions
- profile
- progress
- runtime
- runtime_ms
- memory
- memory_mb
- timestamp
- last_sync
- sync_status
- connect
- disconnect
- import
- dedup

Do not assume the documentation is correct.
Treat actual implementation and tests as authoritative.

Create an internal map of:

1. What currently works
2. What is partially implemented
3. What is broken
4. What is only UI/mock behavior
5. What is undocumented
6. What is documented but not implemented

==================================================
PHASE 2 — DEFINE THE PRODUCTION-GRADE CONTRACT
==================================================

Before coding, establish the expected behavior of the integration.

The integration should have clear separation:

LeetCode transport
    ↓
External models
    ↓
Parser/normalizer
    ↓
Domain mapper
    ↓
Importer/sync service
    ↓
Storage
    ↓
Downstream refresh

Do NOT leak LeetCode-specific response structures into the domain layer.

Do NOT let UI code directly perform low-level LeetCode API operations.

Do NOT duplicate mapping logic between importer, connector and sync.

==================================================
PHASE 3 — FIX DATA MODELS AND NORMALIZATION
==================================================

Audit all LeetCode external models and normalized/domain models.

Ensure fields have consistent names and types.

In particular verify:

- title
- slug
- problem ID
- difficulty
- tags/topics
- platform
- submission ID
- status
- language
- code
- runtime_ms
- memory_mb
- timestamp
- URL
- question/problem metadata

Resolve inconsistencies such as:

runtime vs runtime_ms
memory vs memory_mb
str vs datetime timestamps

Use one canonical representation internally.

Prefer timezone-aware UTC datetimes for persisted timestamps.

Ensure missing/null values are handled safely.

Do not silently corrupt malformed data.

==================================================
PHASE 4 — FIX fetch_user_submissions()
==================================================

Fix the known B4 issue.

The non-empty result path MUST be tested.

It should correctly:

1. Receive external submission data
2. Parse/normalize it
3. Validate required fields
4. Map to CodeMemory models
5. Return valid domain objects
6. Handle missing optional fields
7. Handle malformed records predictably

Do not merely patch attribute names.

Trace the complete data path and make sure all related models agree.

==================================================
PHASE 5 — CLIENT / NETWORK ROBUSTNESS
==================================================

Audit the LeetCode HTTP/client layer.

Make it production-grade within the constraints of the supported public/official interface.

Handle:

- connection failures
- DNS failures
- timeouts
- HTTP errors
- malformed responses
- unexpected response shapes
- rate limiting
- empty responses
- partial responses
- transient failures

Use explicit timeouts.

Do not retry indefinitely.

If retries already exist, verify their behavior.

Use bounded retry/backoff where appropriate.

Do not log secrets or sensitive request information.

Errors should be actionable and safe to display in the UI.

==================================================
PHASE 6 — PAGINATION / COMPLETE DATA RETRIEVAL
==================================================

Determine whether the current implementation retrieves:

- all available submissions
- only one page
- a bounded number
- profile data
- problem metadata
- submission history

If pagination exists, verify it.

If pagination is required by the supported endpoint, implement safe pagination.

Requirements:

- bounded requests
- no infinite loops
- correct page/cursor advancement
- duplicate-page protection
- graceful termination
- partial failure handling

Do not blindly fetch unbounded history.

Provide a configurable sync/import limit where appropriate.

==================================================
PHASE 7 — INITIAL SYNC
==================================================

Make first-time synchronization reliable.

Expected flow:

Connect account
    ↓
Validate identifier/account
    ↓
Fetch supported profile/progress data
    ↓
Fetch supported submission history
    ↓
Normalize
    ↓
Deduplicate
    ↓
Persist
    ↓
Update sync metadata
    ↓
Refresh downstream systems
    ↓
Return SyncResult

The sync result should clearly communicate:

- success/failure
- records fetched
- records imported
- records skipped
- records updated
- duplicates
- errors
- sync timestamp

Do not report success if only part of the operation succeeded unless the result explicitly says partial success.

==================================================
PHASE 8 — INCREMENTAL SYNC
==================================================

Implement or complete incremental synchronization.

Do NOT simply re-import everything every time.

Determine the safest available cursor/watermark using the actual supported LeetCode data.

Possible strategies include:

- latest known submission timestamp
- latest known external submission ID
- server-provided cursor
- another stable external watermark

Choose based on the actual implementation and supported API.

Persist sync state.

Example conceptual state:

SyncState
- platform
- account identifier
- last_successful_sync
- latest_submission_timestamp
- latest_submission_id
- status
- error
- records_fetched
- records_imported

Important:

Never advance the watermark if the sync failed before the relevant data was successfully persisted.

==================================================
PHASE 9 — DEDUPLICATION
==================================================

Audit existing deduplication carefully.

The current project has multiple identifiers/hashes.

Determine the correct identity for:

Problem
Attempt
Submission

Do not rely on an unstable/random identity.

Ensure:

Same submission imported twice
    ↓
one stored submission

Same problem imported repeatedly
    ↓
one problem

A genuinely new submission
    ↓
new submission/attempt as appropriate

Deduplication must work across:

- manual import
- initial sync
- incremental sync
- repeated sync
- application restart

Add tests specifically for this.

==================================================
PHASE 10 — ATOMICITY / PARTIAL FAILURE
==================================================

This is critical for production quality.

Consider what happens if:

100 records fetched
50 persisted
then request/storage fails.

Do not leave the system claiming that all 100 were synchronized.

Use transactions or staged persistence where appropriate.

Ensure sync metadata is updated only after successful persistence.

A failed sync must leave enough state to retry safely.

Retrying must not duplicate already persisted records.

==================================================
PHASE 11 — SYNC STATUS
==================================================

Create/verify a clean sync status contract.

Possible states:

- NOT_CONNECTED
- READY
- SYNCING
- SUCCESS
- PARTIAL
- FAILED

Use the project's existing enums/models if available instead of inventing duplicates.

The UI should be able to display:

Last successful sync
Last attempted sync
Current status
Records imported
Error message if applicable

Do not expose stack traces to normal users.

==================================================
PHASE 12 — ACCOUNT CONNECT / DISCONNECT
==================================================

Audit the account connector.

The account architecture must not store:

- password
- session cookie
- authentication token
- browser session

unless the project explicitly has a legitimate supported authentication mechanism.

Follow the existing project security constraint.

Connection should store only the minimum non-sensitive account identity/configuration needed by the supported integration.

Disconnect should:

- remove account configuration/state
- stop future automatic sync
- preserve existing historical CodeMemory data unless the product explicitly defines otherwise

Do not silently delete historical coding data when disconnecting.

==================================================
PHASE 13 — DOWNSTREAM REFRESH
==================================================

This is a major requirement.

After successful LeetCode synchronization:

LeetCode
   ↓
Storage
   ↓
Analytics
   ↓
Patterns
   ↓
Revision
   ↓
Memory/index
   ↓
Graph
   ↓
Search
   ↓
Ask CodeMemory

Audit which downstream systems actually require rebuilding/reindexing.

Do not blindly rebuild expensive indexes if nothing changed.

But do not leave stale memory/search/graph data after a successful sync.

Implement the smallest correct refresh/invalidation mechanism.

The system should not require restarting the application just to see newly synced data.

==================================================
PHASE 14 — UI INTEGRATION
==================================================

Inspect the Streamlit account/import/settings pages.

The UI must correctly expose:

- account connection
- current connection state
- sync button
- sync progress/state
- last sync time
- imported counts
- errors
- disconnect
- manual import fallback

No fake success states.

No UI should claim "Synced" if the backend returned failure.

No placeholder data should be presented as real LeetCode history.

Avoid network calls directly from presentation components.

The UI should call the service layer.

==================================================
PHASE 15 — CLI INTEGRATION
==================================================

Audit relevant CLI commands.

If LeetCode sync/import commands exist, verify:

- help text
- arguments
- errors
- exit codes
- output
- dry-run behavior if present
- sync status
- limits

CLI should use the same service layer as Streamlit.

Do not duplicate business logic in CLI.

==================================================
PHASE 16 — TESTING
==================================================

This is mandatory.

Current tests are insufficient because the non-empty submission path was not covered.

Add/repair tests for:

### Unit tests

- external model parsing
- normalization
- timestamp conversion
- runtime conversion
- memory conversion
- status mapping
- difficulty mapping
- language mapping
- missing fields
- malformed records

### Connector tests

- empty response
- one valid submission
- multiple submissions
- malformed submission
- network error
- timeout
- HTTP error
- rate limit
- pagination

Mock network calls.

Do NOT make normal unit tests depend on live LeetCode.

### Import tests

- first import
- duplicate import
- repeated import
- mixed new + existing records

### Sync tests

- initial sync
- incremental sync
- no changes
- new submissions
- partial failure
- retry after failure
- sync metadata
- watermark behavior

### Account tests

- connect
- already connected
- disconnect
- invalid account
- no credentials stored

### Downstream tests

After sync verify relevant:

- analytics
- memory
- search
- graph
- revision

are updated/invalidation occurs correctly.

### Regression test

Explicitly add a regression test for B4:

fetch_user_submissions() with a NON-EMPTY response must succeed.

==================================================
PHASE 17 — LIVE INTEGRATION TEST
==================================================

If a live supported LeetCode endpoint can safely be used without credentials:

perform a controlled manual integration test.

Do NOT put live network dependency into normal CI.

Document:

- endpoint used
- request type
- expected response
- observed response
- limitations

If live access requires unsupported authentication, do not work around it.

Manual import remains the fallback.

==================================================
PHASE 18 — DOCUMENTATION
==================================================

After implementation, update ONLY LeetCode-related documentation.

Make sure docs accurately state:

- what is supported
- what is not supported
- whether sync is live
- whether authentication is required
- what data is imported
- sync behavior
- incremental sync behavior
- deduplication
- limitations
- manual import fallback
- security model

Do not claim capabilities that aren't actually implemented.

==================================================
PHASE 19 — PRODUCTION QUALITY CHECK
==================================================

Before finishing, inspect for:

- duplicate logic
- swallowed exceptions
- overly broad except blocks
- missing timeouts
- infinite retry loops
- secret logging
- timezone bugs
- unstable IDs
- inconsistent models
- stale sync metadata
- race conditions
- duplicate records
- partial writes
- stale indexes
- UI/backend mismatch

Use typing consistently.

Keep public interfaces clean.

Do not perform a broad unrelated refactor.

==================================================
PHASE 20 — VALIDATION
==================================================

Run:

1. Focused LeetCode tests
2. Account/sync tests
3. Full pytest suite
4. Coverage
5. CLI validation if relevant
6. Streamlit/backend smoke validation if practical

Report:

- tests before
- tests after
- exact failures fixed
- files changed
- architecture changes
- supported sync behavior
- remaining limitations

Also inspect:

git diff
git status

Ensure no secrets, cookies, tokens, local databases, .env files, or generated artifacts were accidentally modified.

==================================================
IMPORTANT CONSTRAINTS
==================================================

DO NOT:

- use passwords
- ask users for LeetCode passwords
- store LeetCode cookies
- implement browser scraping
- bypass authentication
- use unofficial/private APIs
- fake successful synchronization
- make live network calls mandatory for CI
- weaken tests to make them pass
- modify unrelated CodeMemory subsystems unless required for LeetCode integration
- rewrite the architecture unnecessarily

DO:

- preserve the repository/service abstraction
- reuse existing models and services where appropriate
- fix root causes rather than symptoms
- add regression tests for every discovered bug
- make synchronization idempotent
- make failure/retry safe
- make UI state reflect backend truth
- preserve manual import
- document actual capabilities

==================================================
FINAL ACCEPTANCE CRITERIA
==================================================

Consider the LeetCode work complete only when:

[ ] Non-empty LeetCode submission parsing works
[ ] Runtime/memory fields are correctly normalized
[ ] Timestamp types are consistent
[ ] Connector handles malformed/network responses
[ ] Pagination is correct if required
[ ] Initial sync works
[ ] Incremental sync works or its supported limitation is explicitly implemented/documented
[ ] Sync is idempotent
[ ] Duplicate submissions are not created
[ ] Partial failures are safe
[ ] Sync metadata is reliable
[ ] Account connect/disconnect works
[ ] No credentials/cookies/passwords are stored
[ ] Manual import still works
[ ] Newly synced data reaches storage correctly
[ ] Downstream analytics/memory/search/graph/revision don't remain incorrectly stale
[ ] Streamlit reflects real sync state
[ ] CLI uses the service layer correctly
[ ] Regression tests cover B4
[ ] Network failures are tested without live network dependency
[ ] Full pytest suite passes
[ ] Documentation matches reality
[ ] No unrelated regressions
[ ] No secrets/generated artifacts introduced

DO NOT STOP after fixing B4.

The goal is to make the COMPLETE LeetCode integration reliable end-to-end.