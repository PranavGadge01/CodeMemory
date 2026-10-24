# Final demo readiness report

**Investigation date:** 2026-10-14  
**Decision:** **NO-GO for an end-to-end recording.** Source-level frontend fixes are in place and typecheck passes, but Python tests, a known source API process, synthetic database counts, and every positive browser journey remain unverified.

## 1. Git baseline and changes

- Started on `main`, clean relative to `origin/main` except for a pre-existing staged `A website/tsconfig.tsbuildinfo` and the prior untracked `demo-preparation/` directory.
- Created and moved to `codex/demo-readiness`. The staged file and prior documents were preserved.
- Product files changed on this branch:
  - `frontend/app/(app)/submissions/page.tsx` — typed the page state union and aligned effect dependencies.
  - `frontend/components/app/analytics/submission-patterns-card.tsx` — uses mapper-produced camelCase field names.
  - `frontend/components/app/problems/learning-analysis-card.tsx` — uses mapper-produced camelCase field names.
  - `frontend/components/app/submissions/submission-learning-card.tsx` — uses mapper-produced camelCase field names.
  - `frontend/lib/api/resources.ts` — removed an invalid type re-export from `lib/types`; the public export already comes from `lib/api/mappers`.
- Added this report and appended dated evidence to reports 02, 03, 04, and 08. No product feature, backend route, test, or database file was added or modified.
- The previous runtime database and WAL were inspected only by filename, size, and timestamp. Their contents were not read. No existing runtime data was changed.

## 2. Environment and automated checks

| Check | Result | Evidence / limitation |
|---|---|---|
| Python 3.12 | BLOCKED | `py -0p` says no installed Pythons; `py -3.12 --version` likewise finds none. `python.exe` resolves to the WindowsApps alias and did not provide a usable runtime. |
| `.venv-demo` | NOT CREATED | Confirmed absent. Existing `.venv` was left untouched. |
| Python dependencies and pytest | NOT RUN | Requires the missing Python 3.12. `pyproject.toml` declares `requires-python = ">=3.12"`; default pytest selection excludes `live` tests and uses `pytest -v --tb=short -m 'not live'`. |
| Frontend typecheck | PASS | `npm run typecheck` initially reproduced DTO/domain field mismatches and the missing type export. After the changes, it exited 0. |
| Focused ESLint | FAIL | Five changed files were checked. Three card components retain `react-hooks/set-state-in-effect` findings; the other changed files passed that focused run. |
| Full ESLint | FAIL | `npm run lint` reports 56 errors and 9 warnings. Findings include React hook effect errors and parsing errors in generated `frontend/src-tauri/target/` artifacts. |
| Frontend production build | NOT RUN | `frontend/next.config.ts` sets `output: "export"`; `frontend/out/` already exists. Running a build could overwrite those existing files, so it was not run. |
| Python test suite | BLOCKED | No installed Python 3.12 and no `.venv-demo`. |

### Manual Python installation needed

Use the official [Python 3.12.10 Windows 64-bit installer](https://www.python.org/downloads/release/python-31210/). Python 3.12.15 is now source-only; the official release notes identify 3.12.10 as the last 3.12 release with Windows binary installers. Use the standard full installer, install for the current user, and leave system-wide installation unchecked. Ensure the Python Launcher option is selected. Reopen PowerShell and verify:

```powershell
py -3.12 --version
```

It must report Python 3.12.x. Python's [Windows installation documentation](https://docs.python.org/3.12/using/windows.html) describes per-user full-installer options.

## 3. API and isolated data status

- No process was listening on local ports 3000, 8000, or 8001 during the baseline check. Therefore there was no active API for `/api/v1/health`, `/openapi.json`, route registration, or response-schema inspection. No frontend or API was started during this follow-up.
- Source inspection of `src/api/app.py` shows that the current FastAPI app mounts the routers under `/api/v1`, including insights and learning. `src/api/routes/learning.py` defines the learning routes used by the analytics cards. This proves only what the source app declares, not what an already-running or packaged API returns.
- `src/api/routes/submissions.py` constructs a `SubmissionListOut` with `summary` and `filter_options`; `BaseCamelModel` aliases the response fields to `summary` and `filterOptions`. This is consistent with the frontend DTO and mapper. The earlier undefined `filterOptions`/`statusCounts` crash is not explained by the current source route; stale or mismatched API code is possible but unverified.
- The earlier four analytics-card 404s are not reproducible without an API. The current source app mounts the route implementations. No route has been stubbed, mocked, or hidden.
- `demo-preparation/recording-data/` and `demo-preparation/recording-knowledge/` were confirmed absent and left absent. Existing `demo-preparation/runtime-data/` contents were left untouched.
- Source inspection of `scripts/seed_data.py` shows 22 synthetic DSA problems and 23 submissions: Two Sum has two submissions, and each of the other 21 problems has one. Expected status mix from the literals is 22 accepted and one time-limit-exceeded submission. This is a source-derived expectation only; seed execution, API counts, and storage contents were not verified.

## 4. Blocker disposition

| Reported issue / workflow | Finding | Status |
|---|---|---|
| `/submissions` crashes on missing `filterOptions` or `statusCounts` | Current source route returns those fields under camelCase aliases; there was no active API to test. Frontend now has a typed state, but this does not supply missing API data or suppress errors. | UNRESOLVED / runtime blocked |
| Four analytics learning/insight cards return 404 | Current source mounts learning routes; current running API and responses were unavailable. | UNRESOLVED / runtime blocked |
| TypeScript DTO names and missing `SubmissionListItem` export | Confirmed frontend mapper/domain naming mismatch and wrong re-export source. Corrected. | RESOLVED; typecheck PASS |
| ESLint errors and warnings | Full lint remains failing. React effect errors remain in the changed cards and elsewhere; generated Tauri assets are included by the current lint command. | UNRESOLVED |
| Hydration diagnostics | Not reproduced because Next dev was not started. | NOT TESTED |
| Dashboard totals, problem detail attempts, submission filters, search, revision explanations, analytics, knowledge graph, settings persistence, refresh/restart persistence | Require a seeded source API and browser/API access. | NOT TESTED |
| Login/logout and permissions | No authenticated account flow was identified as needed by the local-first product, and no runtime checks were performed in this follow-up. | NOT TESTED |
| LeetCode connection | Deliberately not attempted; do not enter personal credentials. | NOT TESTED / excluded from demo |

## 5. Exact reproduction commands after Python is installed

Run these from PowerShell at the repository root. The data path is intentionally new and separate from the pre-existing `runtime-data/`.

### Terminal 0 — verify and create the isolated environment

```powershell
Set-Location "C:\Users\Jay Janardan Patil\Desktop\CodeMemory"
py -3.12 --version
if (Test-Path .venv-demo) { throw ".venv-demo already exists; inspect it before proceeding." }
py -3.12 -m venv .venv-demo
& .\.venv-demo\Scripts\python.exe -m pip install --upgrade pip
& .\.venv-demo\Scripts\python.exe -m pip install -e ".[dev]"
& .\.venv-demo\Scripts\python.exe --version
& .\.venv-demo\Scripts\python.exe -m pytest --version
& .\.venv-demo\Scripts\python.exe -m pytest -q
```

Do not run the environment-creation block a second time against an existing `.venv-demo` without inspecting it.

### Terminal 0 — one-time seed, only after checking the paths are still absent

```powershell
if (Test-Path "demo-preparation/recording-data") { throw "Choose a new empty demo data path; do not overwrite it." }
if (Test-Path "demo-preparation/recording-knowledge") { throw "Choose a new empty knowledge path; do not overwrite it." }
@'
from pathlib import Path
from codememory.core.service import CodeMemoryService
from scripts.seed_data import seed_sample_data

base = Path("demo-preparation/recording-data")
knowledge = Path("demo-preparation/recording-knowledge")
db = base / "codememory-demo.duckdb"
service = CodeMemoryService(base_dir=base, knowledge_dir=knowledge, db_path=db)
try:
    seed_sample_data(service)
finally:
    service.close_storage()
'@ | & .\.venv-demo\Scripts\python.exe -
```

This seed is not documented as idempotent. Run it once, only on confirmed absent paths. For a reset-free repeat take, select another new data and knowledge directory name and update every matching API environment variable.

### Terminal 1 — start the source API

Before starting, confirm port 8001 is free. Start only one process against the demo DuckDB file:

```powershell
Set-Location "C:\Users\Jay Janardan Patil\Desktop\CodeMemory"
$env:CODEMEMORY_DATA_DIR = (Join-Path $PWD "demo-preparation/recording-data")
$env:CODEMEMORY_KNOWLEDGE_DIR = (Join-Path $PWD "demo-preparation/recording-knowledge")
$env:CODEMEMORY_DB_PATH = (Join-Path $PWD "demo-preparation/recording-data/codememory-demo.duckdb")
$env:CODEMEMORY_API_HOST = "127.0.0.1"
$env:CODEMEMORY_API_PORT = "8001"
$env:CODEMEMORY_LOG_LEVEL = "INFO"
$env:CODEMEMORY_PROBLEM_SOURCE = "local"
$env:AI_PROVIDER = "heuristic"
$env:PYTHONPATH = (Join-Path $PWD "src")
& .\.venv-demo\Scripts\python.exe -m uvicorn api.app:create_app --factory --host 127.0.0.1 --port 8001
```

Keep this terminal open. After Uvicorn reports ready, use another PowerShell window for read-only checks:

```powershell
$health = Invoke-RestMethod "http://127.0.0.1:8001/api/v1/health"
$health | ConvertTo-Json -Depth 5
$openapi = Invoke-RestMethod "http://127.0.0.1:8001/openapi.json"
$openapi.paths.Keys | Where-Object { $_ -match 'learning|insights|submissions|analytics' } | Sort-Object
$problems = Invoke-RestMethod "http://127.0.0.1:8001/api/v1/problems?page=1&page_size=1000"
$submissions = Invoke-RestMethod "http://127.0.0.1:8001/api/v1/submissions?page=1&page_size=1000"
"problem_count=$($problems.total) submission_count=$($submissions.total)"
```

Readiness requires health/storage `ok`, 22 problems, 23 submissions, and the expected learning routes in `/openapi.json`. If those values differ, stop and investigate before opening the frontend; do not change the seed or fabricate counts to match.

### Terminal 2 — start the frontend only after API checks pass

```powershell
Set-Location "C:\Users\Jay Janardan Patil\Desktop\CodeMemory\frontend"
$env:NEXT_PUBLIC_API_URL = "http://127.0.0.1:8001/api/v1"
npm run dev -- --hostname 127.0.0.1 --port 3000
```

Open `http://127.0.0.1:3000`. Capture API responses and browser-visible results for each workflow in `03_FEATURE_VERIFICATION_REPORT.md` before recording. To stop safely, press `Ctrl+C` in Terminal 2 first and Terminal 1 second; wait for API shutdown before restarting or opening the same DuckDB path in another process.

## 6. Recording order and duration

The prior audit scripts remain the source for narration and segment actions. Use the buyer-facing overview in `06_SHORT_BUYER_DEMO_SCRIPT.md` only after the API and browser checks above pass. Recommended sequence: dashboard → open a seeded problem and show attempt history → submissions and filters → search → revision queue and explanations → analytics and learning cards → knowledge graph → settings, then refresh/restart persistence. Use synthetic records only and keep LeetCode disconnected.

- Full end-to-end cut: approximately 12–18 minutes after all workflows are verified.
- Buyer-facing cut: approximately 4–6 minutes, restricted to the strongest fully verified workflow.
- At present, neither duration is a recording recommendation because no positive workflow has been runtime-verified in this follow-up.

## 7. Priority next actions

1. Install Python 3.12.10 per-user and verify `py -3.12 --version`.
2. Create `.venv-demo`, install `.[dev]`, and run the default pytest suite. Record all failures without altering product behavior to force a pass.
3. Run the isolated one-time seed on the confirmed fresh `recording-data` and `recording-knowledge` paths.
4. Start the source FastAPI API on port 8001, inspect logs, `/health`, `/openapi.json`, problem count, and submission count. Confirm no other process is using the same database.
5. Start the frontend on port 3000 using the explicit API URL. Reproduce `/submissions`, all four learning/insight cards, hydration behavior, and all ten requested workflows using browser and API evidence.
6. Resolve remaining lint failures and review a safe build destination before attempting a build; do not overwrite existing `frontend/out/`.
7. Update the feature matrix and scripts with observed results. Record only after every essential workflow passes.
