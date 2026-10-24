# Feature verification report

## Status definitions

`PASS` means intended behavior was exercised and observed. `PARTIAL` means a limited path/state was observed. `FAIL` means the requested UI behavior errored. `NOT TESTED` means no runtime exercise. `BLOCKED` means an environment or data requirement prevented testing.

## Runtime test matrix

| Feature | Expected | Actual observed | Status |
|---|---|---|---|
| Next frontend startup | Serve UI on localhost | Next 16.3.5 reported Ready; browser opened homepage/routes. First sandboxed start failed Windows canonicalization; retry with execution access worked. | PARTIAL |
| Landing page | Explain product and show preview | Browser showed `PRODUCT PREVIEW · EXAMPLE DATA`, sample 3Sum story and metrics. | PASS for rendering; sample metrics are illustrative |
| Sign-in/auth | Show available auth flow | Source says no account needed; workspace opens directly. No login/session feature to test. | PARTIAL (no auth capability) |
| Dashboard | Show indexed metrics and empty states | UI showed 0 problems/submissions, 0 activity, and illustrative evolution label. | PARTIAL (empty state only) |
| Problem index | Load/filter records | “Showing 0 of 0 problems”; no positive detail/filter test possible. | PARTIAL |
| Revision | Load queue and mark reviewed | Empty queue; no score or mutation tested. | PARTIAL |
| Search | Search stored knowledge | Typed `sliding window`; no results on empty index. Positive retrieval untested. | PARTIAL |
| Analytics core | Load metrics/charts | Zero metrics and honest empty charts loaded. | PARTIAL |
| Analytics learning cards | Load insight, next problem, roadmap, patterns | Four cards displayed `Request failed (HTTP 404).` Source routes exist but active API did not serve those requests. | FAIL in observed environment |
| Knowledge graph | Load nodes/edges | Empty graph state; 0 entities. Node selection unavailable. | PARTIAL |
| Settings | Read preferences/integrations | Preferences loaded, LeetCode disconnected; Codeforces/HackerRank Coming soon; UI says import/rebuild/delete are unavailable. No setting changed. | PARTIAL |
| LeetCode status | Read account state | Username form loaded; no connect submitted. Settings showed Not connected. | PARTIAL |
| Submission log | Render chronological list/details | Next error page. Dev log: `Cannot read properties of undefined (reading 'statusCounts')` at `SubmissionsBrowser`, line 97. | FAIL |
| Import JSON/CSV/JSONL | Validate/import/dedupe records | Source/docs/fixtures/tests exist. Python unavailable; no import run. Current Next UI has no import action. | BLOCKED / NOT TESTED |
| Problem detail/evolution | Show known attempts/code/evolution | No live problem records; not tested. Landing-page 3Sum is illustrative. | BLOCKED |
| Preference persistence | Change and reload | Not tested; no write made because API ownership/path were not independently verified. | NOT TESTED |
| Multi-account isolation | Switch users and confirm scoping | Source and tests exist; no accounts/writes created. | NOT TESTED |
| Authenticated sync | Store/validate credentials and full sync | No credentials entered; requires user-owned session/CSRF and network. | NOT TESTED |
| CLI/Streamlit | Run Python surface | `.venv` points to missing Store Python 3.13; launcher found no installed Python. | BLOCKED |
| Clean API startup/health | Start explicit isolated API, verify health | Packaged `dist/codememory-api.exe` returned without diagnostics; it created an isolated DB/WAL but listener/health could not be independently confirmed. Frontend read routes responded, but owning process/path could not be attributed. | BLOCKED for clean startup; limited route responses observed |
| Tauri | Start desktop shell/sidecar | Config/spec inspected only. | NOT TESTED |

## Automated checks

| Check | Result | Limit |
|---|---|---|
| Python pytest (`python -m pytest -q`) | Not run: `.venv\Scripts\python.exe` could not start; `py` found no installed Python. | Requires new Python 3.12 env. Default suite excludes tests marked `live`. |
| Frontend `npm run typecheck` | FAIL; numerous TypeScript errors, including snake_case use against camelCase mapped types and missing `SubmissionListItem` export. | Not a release build. |
| Frontend `npm run lint` | FAIL: 57 errors, 10 warnings; includes `no-explicit-any` in submissions page and generated Tauri target assets. | Command still fails; source and generated-output findings should be separated in a future fix. |
| Browser walkthrough | Local Next dev server via Codex in-app browser. | Read-only navigation and one search. No mutation, seed, import, or external LeetCode action. |

## Source observations (not runtime claims)

- `src/api/app.py` registers health, dashboard, problems, submissions, analytics, knowledge, revision, LeetCode, search, insights, learning, and settings routes.
- `frontend/lib/api/client.ts` has no mock fallback on network failure. `frontend/lib/data.ts`/`frontend/lib/mock/` power the marketing preview.
- `scripts/seed_data.py` creates 22 synthetic problems. It was not run.
- CLI `seed` constructs default `CodeMemoryService()`; do not run against current `data/`.
- Tests under `tests/` and `tests/api/` cover many domains, but their existence is not evidence they passed here.

## Demo decision

Do not claim a complete end-to-end workflow was proven. The only complete browser path verified was a read-only empty-state tour. Before a buyer recording, restore Python, launch a known API against isolated synthetic data, and retest positive flows. Resolve the submissions crash and four HTTP 404 cards before showing those features as working.

## Readiness follow-up — 2026-10-14

This follow-up separates newly confirmed source/test evidence from runtime evidence:

| Area | Evidence now available | Status |
|---|---|---|
| API route registration | Source inspection of `src/api/app.py` shows the `/api/v1` router mounts for submissions, analytics, insights, and learning. `src/api/routes/learning.py` defines `/learning/patterns`, `/learning/profile`, `/learning/recommendations`, `/learning/roadmap`, submission learning, and problem learning-analysis routes. No API process was listening on ports 8000/8001, so no active OpenAPI document or live response was inspected. | PARTIAL (source only) |
| Submission response contract | `src/api/routes/submissions.py` constructs `SubmissionListOut` including `summary` and `filter_options`; the Pydantic camel alias in `src/api/schemas/common.py` exposes those as `summary` and `filterOptions`. The frontend mapper expects those names. The previously observed crash cannot be attributed to the current running API because no API was active. | PARTIAL (source only) |
| Frontend domain mapping | Three cards were reading wire-format snake_case after mapper functions converted the DTOs to camelCase. Those reads now use the mapped names. The submissions page state is typed as a discriminated union, and the invalid `SubmissionListItem` export was removed from the wrong module. | PASS (frontend typecheck) |
| Frontend typecheck | `npm run typecheck` initially reproduced DTO naming and export errors. After the corrections on `codex/demo-readiness`, the same command exited successfully. | PASS |
| Frontend lint | `npm run lint` after the corrections reports 56 errors and 9 warnings. The focused lint of the changed TSX files still reports three existing `react-hooks/set-state-in-effect` errors. Generated Tauri files under `frontend/src-tauri/target/` also produce parsing errors under the current lint config. | FAIL |
| Python tests | Python 3.12 is not installed and `.venv-demo` was not created. The suite was not run. | BLOCKED |
| API/browser workflows | No local listener existed on ports 3000, 8000, or 8001. No API was started and no browser workflow was exercised in this follow-up. | NOT TESTED |
| Hydration diagnostics | Not reproduced because the frontend dev server was not started. | NOT TESTED |

The `/submissions` undefined-value report and four analytics-card 404s remain unresolved runtime findings. Current source declarations do not reproduce them; an old or mismatched API process is plausible but unverified. Do not present those routes as verified until the freshly started source API returns the expected routes and response schemas.
