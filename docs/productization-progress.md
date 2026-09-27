# Productization checkpoint — 2026-09-27

## Status

All six phases are implemented and verified as far as this environment allows.
Phase 1's submission-link fix and every later phase were completed without a
commit or push; the working tree is the deliverable.

- **Phase 1 — complete.** Submission links, typecheck, static build, API tests and
  static route checks passed.
- **Phase 2 — complete.** Additive, data-preserving account-ownership migration;
  account-scoped review state, notes, priority, due state, revision metadata,
  search, semantic search and memory; credential revocation; verified copy
  migration to `%LOCALAPPDATA%\CodeMemory`; hidden, supervisor-owned sidecar.
- **Phase 3 — complete.** Intro → username → public sync → dashboard onboarding,
  honest empty states, serialized optimistic settings with rollback, scoped
  revision topics.
- **Phase 4 — complete locally.** Independent static `website/` with `/` and
  `/download`; publication still pending a real release.
- **Phase 5 — complete locally.** MSI and NSIS rebuilt, inspected and checksummed;
  `perMachine` install mode removes the install-directory/data-directory
  collision. Silent per-machine install needs an elevated interactive session.
- **Phase 6 — complete.** Ignores audited without deleting data; documentation
  written; full backend, frontend, website, Cargo and Playwright regression run.

The final numbers for every phase are consolidated under
"Final verification — 2026-09-27" at the end of this document; earlier interim
runs in this file are superseded by that section.

## Starting state and architecture

- Branch: `fix-submissions-ui`; starting HEAD: `d8dbf31`.
- Pre-existing working-tree entries: modified `frontend/src-tauri/Cargo.toml`,
  untracked `.claude/settings.local.json`, and untracked `PHASE_GUIDE.md`.
  These were preserved. Cargo.toml had no textual Git diff.
- Desktop: Tauri 2, Next.js 16.3.5 static export, FastAPI, canonical DuckDB,
  and filesystem/Parquet exports through `CompositeStorage`.
- Tauri bundles `dist/codememory-api.exe`, built using
  `backend/codememory-api.spec`. Production resources already accommodate
  Tauri's `_up_/_up_/dist/` layout.
- Submission detail is the client-side `/submissions?id=<id>` route.
- Account connections are JSON metadata; submissions have account provenance.
  The credential vault uses encrypted files and a per-account key in OS keyring.
- Runtime paths currently default to relative `data/` and `knowledge/`.
  The Tauri sidecar inherits the launching process's working directory.
- The PyInstaller executable is currently built with `console=True`; Rust does
  not currently specify a hidden-window creation flag.
- Existing tests cover API routes, authenticated sync, multi-account sync,
  persistence, revision, search, and memory isolation. Passing these tests does
  not establish isolation of shared review records; see the reproduction below.

## Six-phase implementation plan

| Phase | Work and verification |
| --- | --- |
| 1 — Correctness | Repair main submission links without changing the API, drawer, or route architecture. Check detail fields and navigation, then typecheck and static build. |
| 2 — Desktop hardening | Resolve the ownership model below; fix query and mutation boundaries with regression tests. Audit credential disconnect/revoke/reconnect. Design a copy-preserving app-data migration after inspecting all runtime paths. Harden hidden startup, health ownership, port conflicts, shutdown and restart. Run backend tests, Cargo checks and production desktop builds. |
| 3 — Product UX | Reuse existing tokens/components for intro → username → public sync → dashboard. Persist onboarding locally; recognize existing accounts and disconnection. Replace fake values with actual data or honest empty states. Improve settings loading/errors/rollback. |
| 4 — Website | Build an independent static `website/` with `/` and `/download`, shared brand language, supported feature descriptions, actual available screenshots, and centralized release configuration. Verify responsive layouts, links and production build. |
| 5 — Release | Establish one version source, verify MSI/NSIS contents, install/upgrade/persistence and full smoke flows. Configure real versioned artifact URLs; publish only when a concrete release is ready and publication is authorized. |
| 6 — Regression/docs | Update authentication/pagination, desktop/sidecar, website/release, data-path and migration docs. Audit ignores without deleting runtime data. Run full relevant backend/frontend/Cargo/Tauri checks and report remaining failures. |

No commits, pushes, resets, branch changes, or release publication were made.

## Phase 1 changes

`frontend/components/app/submissions/submissions-browser.tsx`:

- The problem-title link in each submission row now opens that submission's
  encoded `/submissions?id=...` URL, instead of `/problems?slug=...`.
- The submission-ID link remains usable when its problem is outside the loaded
  problem page and the row has placeholder metadata.
- The title link's tooltip now describes opening a submission.

The Problem drawer, submission-detail component, API, Tauri routing and static
export configuration were left intact. Inspection confirmed the drawer already
uses the canonical query-string route and encodes submission IDs.

## Verification results

| Check | Result |
| --- | --- |
| `npm run typecheck` in `frontend/` | Passed. |
| `npm run build` in `frontend/` | Passed; all 13 static pages generated. |
| API suite (`tests/api`) | **75 passed**, one dependency deprecation warning, 26.78 seconds. |
| Static HTTP navigation targets | HTTP 200 for dashboard, problems, problem query detail, submissions, submission query detail, analytics, knowledge, revision, search, and settings. |
| Submission API detail, isolated account fixture | HTTP 200; ID, problem/attempt IDs, Accepted status, Python language, 3 ms runtime, 14.5 MB memory, UTC timestamp, `fixture-a` source account, and source code present. |
| Analytics API (`/api/v1/analytics`) | HTTP 200. |
| Drawer link and detail UI source inspection | Canonical encoded query link retained; detail renders status, language, runtime, memory, timestamp, source account and code, with missing-code state. |
| `git diff --check` | Passed. |
| Interactive click-through / visual layout | Not verified: no browser was available through browser automation. HTTP checks do not exercise hydration or clicks. |
| Windows installer, WebView2, Cargo and Tauri build | Not run at this checkpoint; desktop code was not changed. |
| Live public/authenticated LeetCode sync | Not run; fixture tests do not establish live service behavior. |

The initial Node checks failed with sandbox `EPERM` during workspace path
resolution. Both checks passed after approved execution outside the sandbox.
The virtual environment's Microsoft Store Python base executable also required
approved execution outside the sandbox.

Tests and temporary servers used isolated data under ignored
`build/phase1-checks/`; the user's real database and credentials were not used.
The API suite ran with that directory as its working directory because some
existing in-memory fixtures still use relative filesystem export paths.

The audit initially requested `/api/v1/analytics/overview`, which returned 404;
inspection established that the existing route is `/api/v1/analytics`, and the
correct route passed. This was a probe error, not an application regression.

## Phase 2 original finding: account ownership of shared state

### Reproduced behavior

An in-memory canonical database was seeded with:

- A shared problem containing one A submission and one B submission, both
  30 days old, with separate attempts.
- A second problem containing only a B submission.
- Account A active through an isolated `AccountService`.

The current code produced these results:

| Operation | Observed result | Required result |
| --- | --- | --- |
| A reviews the shared problem | HTTP 200; B's revision age changes from **30 days to 0**. | Only A's review state changes. |
| A posts a review for B's exclusive problem | HTTP 200. | Reject without mutating B's data. |
| B retrieves the shared problem after A's review | A's review note is included. | A's private review note is absent. |
| A calls `CodeMemoryService.search(query="b-only")` | B's exclusive problem is returned. | No result. |
| Disconnect, then `get_problem("two-sum")` | Submissions from both A and B are returned. | Connected-account data remains inaccessible. |

These results were reproduced against the unchanged backend. The existing
75 passing API tests do not cover these cases.

### Why filtering alone is insufficient

`ProblemNote` and the DuckDB `notes` table have no account owner. Reviews write
to shared `Problem.updated_at` and append an unowned note. Filtering submissions
cannot determine who owns an existing note or timestamp. Attempts also contain
reasoning, mistakes, status and activity timestamps that can outlive or combine
submissions from multiple accounts.

`list_problems()` and `get_problem()` copy and filter submissions, but leave
shared notes and attempt metadata intact. `get_problem()` also returns the
original attempts when no unscoped submissions survive its disconnected filter.
`SearchService` reads raw storage. Revision priority reads the complete shared
problem; the API queue filters problem membership but then scores that shared
history. The mutation endpoint does not validate active ownership at all.

### Affected implementation areas

- `src/codememory/domain/models.py`: `ProblemNote`, `Attempt`, `Problem`.
- `src/codememory/core/service.py`: scoped projections, search, revision and
  disconnected reads.
- `src/codememory/revision/revision_service.py`: priority, due queue and review
  mutation; `src/api/routes/revision.py`: route-to-service boundary.
- `src/codememory/search/search_service.py` and `semantic_search.py`: scoped
  input, including private notes and attempt reasoning; account-safe indexing.
- `src/codememory/storage/duckdb_repository.py`, `composite_repository.py`,
  `fs_repository.py`, `parquet_repository.py`: schema migration and export parity.
- Memory document generation, analytics and knowledge projections consuming
  shared notes/attempt metadata need corresponding isolation regression checks.

### Options and recommendation

1. **Recommended: additive account ownership and separate review state.** Keep
   shared problem definitions and existing submission identities. Add nullable
   provenance for private notes/attempt metadata and an account/problem review
   record. Route reads and writes through explicit account context. This fixes
   shared-problem isolation without replacing the existing storage architecture.
2. **Separate databases per account.** This gives a stronger physical boundary,
   but requires splitting existing histories and revisiting sync, deduplication,
   exports and active-account switching. It is substantially more disruptive.

A membership check alone is a useful partial guard, but is not a complete
solution: A and B can both legitimately own submissions for the same problem.

### Approved migration design

1. Add nullable owner provenance to private notes and attempt metadata, and an
   `account_problem_reviews` record keyed by provider, account and problem ID
   with `last_reviewed_at`. A review must not overwrite the shared problem's
   activity timestamp. Preserve existing problem and submission IDs.
2. Make an idempotent additive DuckDB migration with a recoverable backup before
   modifying an existing database. Preserve filesystem/Parquet exports and
   update their serializers to retain provenance on subsequent writes.
3. Attribute legacy records only where ownership is unambiguous. Keep ambiguous
   records unchanged as legacy data, excluded from connected-account private
   views until explicitly assigned. Do not copy an unowned note into every
   account, guess its author, or delete it. Preserve manual/offline records.
4. Build account-specific projections before scoring/searching/indexing.
   Derive account activity and accepted/failed status from matching submissions
   and account-owned reviews; omit another account's private attempt metadata.
   Mutations verify membership against raw canonical storage and update only
   the owned record, never save a filtered problem over the full history.
5. Carry active context through service/domain operations and API entry points,
   covering connected, disconnected, switched, and explicit account requests.
6. Add regressions for shared and exclusive problems, cross-account writes,
   legacy records, disconnected reads, review persistence/restart, search and
   semantic snippets, and migration reruns. Remove cross-account cache reuse.
7. Re-run relevant backend and API suites before proceeding to credential,
   runtime-directory and sidecar work. Preserve public API and static route
   shapes wherever possible.

This migration was explicitly approved. The latest instruction authorizes all six phases without approval gates.

## Phase 2 implementation checkpoint

- Additive ownership migration `account_ownership_v1` implemented. Private notes,
  attempt metadata, review/priority/due state, search, memory and derived views are
  account-scoped. Ambiguous legacy state uses `__codememory_legacy_unassigned__`;
  it is preserved and excluded from connected-account views, never guessed.
- The migration to `%LOCALAPPDATA%\CodeMemory` was performed. Every copied file
  was hash-verified. All original fields in **79 problems, 174 attempts, 111
  submissions and 0 canonical notes** matched before and after migration.
  `ownership-verification.json` records the comparison. The original `data/` and
  `knowledge/` remain, alongside the destination's pre-ownership database backup.
- Disconnect revokes the active account's encrypted credentials. Revoke preserves
  its public connection. Switching accounts keeps each account's separate vault;
  reconnecting a disconnected account requires credentials again. A revocation
  marker prevents failed keyring cleanup from reviving an old credential.
- Hidden sidecar startup, per-launch health identity, bounded readiness, port
  conflict errors, crash reporting and Windows Job Object tree cleanup implemented.
- Verification: **116 checkpoint tests passed** (all 75 API tests, account sync,
  isolation, runtime migration, AI/memory regressions). Latest full suite had
  **664 passed / 1 stale-mock failure**; that mock was fixed and the checkpoint
  covers it. Frontend typecheck/build, PyInstaller and Cargo check passed.
  Final full suite and rebuilt installers follow below.
- Important files: ownership/domain/storage/core/search/memory/revision/analytics
  modules; LeetCode service/vault; API account context; runtime migration script;
  Tauri sidecar/process_job; ownership and runtime regression tests.
- Interactive WebView2 and live authenticated sync remain to be checked where
  technically possible; fixture success is not claimed as live account validation.

## Phase 3 — verified

- Production static build/typecheck passed. Full backend suite: **667 passed**,
  one live test deselected. Subsequent additional ownership tests: **11 passed**.
- Real Edge browser against the real isolated API/DuckDB (only remote LeetCode
  transport stubbed): intro → username → public sync → dashboard; returning
  launch; submission title → query detail → account-specific code; A → B switch;
  revision topics/review; settings disconnect; navigation all passed.
- Concurrent optimistic settings failure/success and reload persistence passed.
- Browser regression exposed cached-theme hydration mismatch and concurrent
  analytics cursor interference; both fixed. Added parallel API read regression.
- Auth validation now preserves the public connection when optional credentials
  are absent/invalid. API regression confirms the two states remain independent.
- Files: app/page.tsx, app/connect/page.tsx, lib/onboarding.ts, settings provider/
  view/account section, topbar, revision workspace/API, settings API, LeetCode API,
  analytics locks, Playwright configuration/tests and isolated test server.

## Phase 4 — verified locally

- The public site is a standalone static Next.js export in `website/`. It has no
  FastAPI, DuckDB, Tauri, credential or runtime-data dependency; the only external
  input is `../release.json`, read at build time.
- **Homepage recovery.** The first Phase 4 pass wrote a simplified hand-built
  homepage. That was replaced, at the maintainer's direction, with the product
  homepage the desktop application shipped before productization:
  `frontend/app/page.tsx` at `d8dbf31` (431 lines). The recovered page is ported
  with its sections, hierarchy, product window, charts, knowledge graph, revision
  queue and animation intact. See "Website homepage recovery" below for the exact
  difference.
- Routes: `/`, `/download`, `/about`, `/contact`, `/privacy`, `/terms`,
  `/changelog` and a 404 page. Pages exist only where there is real content — no
  empty docs or releases routes.
- CTA rules are enforced by test: `Connect LeetCode`, `Open CodeMemory`,
  `Browse problems`, `Open queue` and the demo rows all resolve to `/download`;
  no page links to `/connect`, `/auth/sign-in`, `/dashboard`, `/problems`,
  `/revision` or `/settings`.
- `release.json` centralizes version, repository and platform/artifact metadata.
  It is read by `next.config.ts` and inlined into the build, so the app never
  reaches outside `website/` at build time. While `published` is false the
  download buttons render disabled and no artifact URL is emitted;
  `CODEMEMORY_RELEASE_DIR` builds a self-hosted site and copies local installers
  into `out/releases/v<version>/`.
- Website typecheck, production export and **11 tests passed**. Playwright
  checked the homepage, download page, supporting pages and 404 at **1440, 768
  and 390px** with no horizontal overflow; screenshots in `build/browser/`.
- Files: `website/{app,components,lib,public,scripts}/`, `website/package*.json`,
  `website/tsconfig.json`, `website/next.config.ts`,
  `website/postcss.config.mjs`, `website/tests/site.test.mjs`,
  `website/README.md`, `scripts/serve-static.mjs`, `release.json`.
- The GitHub repository currently has no published releases. Public release
  hosting and deployment remain external work; no nonexistent download is claimed.

## Phase 5 — installers built and verified

- `release.json` is version authority; `scripts/sync-version.mjs --check` verifies
  frontend/Python/Tauri/Cargo/website values. Current version: **0.1.0**.
- Windows build workflow and verified artifact collection/checksums prepared.
- Final backend suite: **670 passed**, one live test deselected.
- Distribution defect found and fixed: Tauri's default `currentUser` NSIS install
  directory is `%LOCALAPPDATA%\CodeMemory` — the same folder as the runtime data
  store. `bundle.windows.nsis.installMode` is now `perMachine` (matching the MSI),
  so program files can never share a directory with user history, notes or
  credentials, and a manual delete of the install folder cannot destroy user data.
- Both installers were rebuilt and inspected. Each contains the static frontend
  inside `app.exe` plus the bundled sidecar (`_up_\_up_\dist\codememory-api.exe`,
  147 MB). Verified copies and SHA-256 checksums are in `build/release/`.
- Production sidecar smoke test on an isolated app dir: PE subsystem **2** (no
  console window), health `ok` with a per-launch instance identity, settings
  (theme + density) persisted across a full stop/restart, database created under
  the app dir, `logs/sidecar.log` written, legacy source untouched, and no stale
  listener or orphan process after terminating the tree.
- A silent per-machine install cannot be verified without administrator rights in
  this session; see remaining issues. Existing generated directories and any
  legacy runtime files inside them are preserved.

## Phase 6 — cleanup, documentation, final regression

- Generated artifacts audited with `git check-ignore`: `website/node_modules`,
  `website/out`, `frontend/node_modules`, `frontend/.next`, `frontend/out`,
  `frontend/src-tauri/target`, `frontend/test-results`, `build/`, `dist/`, `.rust/`,
  the DuckDB files and `*.pre-ownership-v1.bak` are all ignored. No runtime user
  data or required build directory was deleted.
- Documentation added/updated: `docs/windows-release.md` (development, sidecar,
  build, test, installer contents, runtime behaviour, versioning, publication),
  `docs/data-migration.md` (ownership model, legacy attribution, `%LOCALAPPDATA%`
  paths, copy/verify/switch, recovery, credential lifecycle),
  `website/README.md` (build, output, deployment assumptions, release config),
  plus `README.md`, `docs/development.md`, `docs/leetcode-integration.md` and
  `docs/leetcode-auth.md` for authenticated pagination and the current desktop
  flow. Obsolete "no credentials anywhere" wording was corrected.
- Final regression executed: full backend suite, frontend typecheck/static build,
  `cargo check`, `npm run tauri build`, website typecheck/build/tests and the
  Playwright desktop flow. Results are recorded above and in the final report.

## Final verification — 2026-09-27

Every result below was produced after the last code change. Nothing was committed
or pushed; `git status` still shows the full working tree described at the end of
this file.

### Backend

- Full suite from an isolated working directory:
  `670 passed, 1 deselected, 1 warning in 268.02s` (the deselected test is the
  live-network LeetCode test).
- Account-isolation and runtime-migration regression files re-run:
  `tests/test_productization_ownership.py` (11) plus
  `tests/test_runtime_migration.py` (3) → **14 passed**.

### Ownership migration on the real store (proof of data preservation)

`build/phase2-tests/verify_repo_ownership.py` copies the real repository store to
a temporary directory, opens it through `DuckDBStorage` (which checkpoints,
backs up, then migrates), and compares the before/after tables:

- rows `problems` 79 / `attempts` 174 / `submissions` 111 / `notes` 0, identical
  before and after;
- every pre-existing column value byte-identical (`content_unchanged: true`); the
  only differences are the new columns `attempts.source_account`,
  `attempts.mistakes_json`, `attempts.analysis_json` and `notes.source_account`;
- `schema_migrations` contains `account_ownership_v1`;
  `account_problem_state` gains one row per problem (79);
- zero attempts remain unowned; legacy attribution resolved deterministically to
  `jaypatil1229` (113), `__codememory_legacy_unassigned__` (21),
  `shrey_sawant` (20) and `agOY76a5Qu` (20);
- the backup `*.pre-ownership-v1.bak` byte-matches the pre-migration database and
  the source store is untouched.

Runtime store `%LOCALAPPDATA%\CodeMemory` (383 files, including the 92-problem
`knowledge/` tree) holds the same 79/174/111/0 rows with `account_ownership_v1`
applied, `account_problem_state` = 79 rows and a verified `.bak`; the repository
`data/` store is left in its legacy shape on purpose and migrates on first dev
open, with a backup.

### Frontend and desktop

- `npm run typecheck` — clean.
- `npm run build` — static export, 13 routes prerendered.
- `cargo check` in `frontend/src-tauri` — `Finished dev profile` in 21.63s.
- `npm run tauri build` — `Finished 2 bundles`; rebuild log
  `build/tauri-rebuild.log`.
- Playwright end-to-end (`npm run test:e2e`) — **3 passed in 18.1s**: first
  launch → public sync → returning launch → submission detail → account switch;
  failed optimistic settings patch preserving the later successful patch and
  surviving reload; website homepage/download responsive and independent.

### Installers

- NSIS `CodeMemory_0.1.0_x64-setup.exe` (149,659,118 bytes) — contains `app.exe`
  and `_up_\_up_\dist\codememory-api.exe`; generated `installer.nsi` defines
  `INSTALLMODE "perMachine"` and resolves `$INSTDIR` to
  `$PROGRAMFILES64\CodeMemory`.
- MSI `CodeMemory_0.1.0_x64_en-US.msi` (150,855,680 bytes) — contains the same two
  files; its `main.wxs` references no runtime `data/` or `knowledge/` content.
- `build/release/SHA256SUMS.txt`:
  `66e14426c795e60d2790ad023b063f1f8b408655c62018e0a1c60e8edb437356` (NSIS),
  `b1d0147744108acc1693edeaf10c990383461eeb02b922147bded4036ae8ea37` (MSI).

### Website

- `node scripts/sync-version.mjs --check` → `Release versions consistent: 0.1.0`.
- `npm --prefix website run typecheck` — clean.
- `npm --prefix website run build` — static export of `/`, `/about`, `/changelog`,
  `/contact`, `/download`, `/privacy`, `/terms` and the 404 page into `website/out`.
- `npm --prefix website test` — **11 passed** (every route standalone with valid
  internal links, the recovered product sections present, no desktop routes on
  any page, download availability matching `release.json`).

### Known leftover

`frontend/src-tauri/target/release/bundle/msi/` still contains an old `data/` and
`knowledge/` tree from an earlier manual run of `app.exe` with that folder as the
working directory. It is inside a git-ignored build directory, is not referenced
by the WiX or NSIS scripts, and is not shipped in either installer. It was left in
place rather than deleted.

### Website homepage recovery — 2026-09-27

The website homepage is the product homepage recovered from Git, not a new design.
`build/recovery/old-page.tsx` (extracted from `HEAD~1`, i.e. `d8dbf31`) and
`website/app/page.tsx` differ only in:

- a nine-line header comment recording the provenance;
- one added import for the shared public footer;
- five destinations — `/dashboard` (×2), `/revision`, `/problems?slug=<slug>` and
  `/problems` — changed to `/download/`;
- the inline footer function removed, because the same markup now lives in
  `components/site/site-footer.tsx` with the public page links.

Everything else — the six sections (`product`, `memory`, `evolution`, `analytics`,
`knowledge`, `revision`), the hero product window, the activity heatmap, recent
memory timeline, solution-evolution panel, weekly-submission bar chart, language
distribution, difficulty cards, knowledge graph, revision queue and the closing
call to action — is byte-identical, together with the design tokens in
`app/globals.css` and the copied `components/{ui,system,charts,app,home}`,
`lib/mock` and `lib/format` modules.

Two components were adapted for the public site only:

- `components/system/theme-toggle.tsx` uses the local theme store instead of the
  desktop settings store (the website has no backend); the markup is unchanged.
- The demo rows in `components/app/timeline.tsx` and
  `components/app/knowledge/knowledge-graph.tsx` link to `/download/` rather than
  the workspace problem route.

Verified in a real browser: all six sections render, all twelve reveal-on-scroll
elements reach their visible state, and the homepage, download page, supporting
pages and 404 render at 1440/768/390px without horizontal overflow.
