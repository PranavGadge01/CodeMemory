# Run and test guide

## Current workstation status

- Node.js v22.23.2 and npm 10.9.8 are available. Frontend packages are already present.
- `npm run dev` starts Next after Windows path access is allowed; the browser reached `http://127.0.0.1:3000`.
- The repo `.venv` is unusable: it was created against a missing Microsoft Store Python 3.13 executable. `py` reports no installed Python. Bundled Python 3.12.14 lacks pytest and application dependencies.
- The prebuilt `dist/codememory-api.exe` returned immediately with no useful output. A clean API startup was not confirmed.
- That attempt created an isolated `demo-preparation/runtime-data/codememory-demo.duckdb` and WAL file, but no seed was run. These are not the recommended recording paths; use a fresh `recording-data` or `streamlit-profile` directory instead. I left them in place because their file-handle state could not be confirmed safely.
- The configured API did answer several read-only UI requests. Its process and data path are unknown, so no write request was made.

## Safe setup before recording

Install Python 3.12 from the official Python for Windows distribution, enable the Python Launcher, and open a new PowerShell window. Confirm `py -3.12 --version` prints 3.12.x. This manual install has not been performed here. Do not overwrite `.venv`; create a new environment:

```powershell
py -3.12 -m venv .venv-demo
& .\.venv-demo\Scripts\python.exe -m pip install --upgrade pip
& .\.venv-demo\Scripts\python.exe -m pip install -e ".[dev]"
& .\.venv-demo\Scripts\python.exe --version
& .\.venv-demo\Scripts\python.exe -m pytest --version
node --version
npm --version
```

Pip may need network access. These commands create `.venv-demo` only; they do not change application source.

## One-time isolated synthetic seed (not yet run)

`scripts/seed_data.py` creates 22 synthetic classic DSA problems with attempts, submissions, and knowledge files. Do not run `codememory seed` against this checkout: the CLI constructs `CodeMemoryService()` with default paths and ignores the API path variables. Seed once into a fresh dedicated directory before starting the API. First confirm the two target folders do not already contain user work.

```powershell
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

The seed is not documented as idempotent; run it once on a fresh folder. For another take, choose a new folder name in this snippet and the API variables. Never mix a real export into it.

## Start API — PowerShell terminal 1

From repo root; use exactly the same paths as the seed. API configuration reads these variables at startup. Explicit provider selection keeps analysis offline.

```powershell
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

Expected readiness: Uvicorn listens on `127.0.0.1:8001` without startup errors. Verify `http://127.0.0.1:8001/api/v1/health` reports overall/storage `ok`. Keep this terminal for troubleshooting; do not show environment setup while recording.

## Start frontend — PowerShell terminal 2

```powershell
Set-Location .\frontend
$env:NEXT_PUBLIC_API_URL = "http://127.0.0.1:8001/api/v1"
npm run dev -- --hostname 127.0.0.1 --port 3000
```

Open `http://127.0.0.1:3000`. The value in `frontend/.env.local` is not reproduced here; process variable above sets the demo API origin for this terminal. The audited dev server emitted hydration diagnostics; use a production build only after type errors are resolved and the build succeeds.

## Optional legacy surfaces

- `codememory ui` launches Streamlit; `run.ps1` installs dependencies and runs `src/codememory/app/app.py` on port 8501. Do not run either with the repository root as working directory: their service defaults to relative `data/` and `knowledge/`.
- For a safe import-first legacy workflow, create a fresh isolated working directory and set Python import paths to the repo. Use a new profile name if this folder already exists:

```powershell
# Run from the repository root; first confirm this path does not contain work.
$repo = (Resolve-Path .).Path
$profile = Join-Path $repo "demo-preparation/streamlit-profile"
if (Test-Path $profile) { throw "Choose a new empty profile directory; do not overwrite existing work." }
New-Item -ItemType Directory -Path $profile | Out-Null
Set-Location $profile
$env:PYTHONPATH = "$repo\src;$repo"
& "$repo\.venv-demo\Scripts\python.exe" -m streamlit run "$repo\src\codememory\app\app.py" --server.port 8501 --server.headless true --browser.gatherUsageStats false
```

The app’s default relative storage now resolves inside `streamlit-profile/`. Open `http://127.0.0.1:8501`. To import a fully synthetic fixture, choose **Data Import**, select **LeetCode Export Dataset (JSON / CSV)**, upload `$repo\tests\fixtures\leetcode\sample_leetcode.json`, inspect **LeetCode Normalization & Validation Preview**, then select **Confirm & Import LeetCode Dataset** once. The fixture has six synthetic submissions. Stop Streamlit before starting any second process against the same DuckDB file.

- The Next/API demo may reuse that isolated profile after Streamlit is stopped. Start API from repo root with `CODEMEMORY_DATA_DIR` set to `demo-preparation/streamlit-profile/data`, `CODEMEMORY_KNOWLEDGE_DIR` to `demo-preparation/streamlit-profile/knowledge`, and `CODEMEMORY_DB_PATH` to `demo-preparation/streamlit-profile/data/codememory.duckdb`; then start the frontend as above. This is an alternative to the 22-problem seed; do not run both into the same profile.
- Tauri uses `npm run tauri:dev`; config uses `http://localhost:3000` and a bundled sidecar. Not tested. Tauri CSP lists API port 8000, while the frontend example uses 8001; verify before choosing desktop for a recording.

## Tests and checks

After environment setup, from repo root:

```powershell
& .\.venv-demo\Scripts\python.exe -m pytest -q
```

Pytest defaults exclude `live` network tests. From `frontend/`:

```powershell
npm run typecheck
npm run lint
```

Current observations: typecheck fails on numerous errors; lint reports 57 errors/10 warnings, including generated Tauri output. A dev server response is not proof of a clean release build.

## Safe shutdown and preflight

Stop terminal 2 with `Ctrl+C`, then terminal 1 with `Ctrl+C`; wait for API shutdown. Keep the synthetic folders for another take. Do not clear/reset repository data.

- [ ] Python 3.12 environment and pytest work.
- [ ] Dedicated paths were empty before one-time seed.
- [ ] API logs show clean startup; health/storage says `ok`.
- [ ] Frontend uses port 8001 API origin.
- [ ] Dashboard, problem detail, submissions, revision, search, graph, settings reload, and AI cards all work with seeded records.
- [ ] Typecheck/lint blockers resolved; no error overlay/hydration error.
- [ ] LeetCode disconnected; no real account data or credentials on screen.
- [ ] Synthetic data only; screen and notifications prepared per checklist.

## Readiness follow-up — 2026-10-14

- Baseline was checked on branch `main`; work is now on `codex/demo-readiness`. The pre-existing staged `website/tsconfig.tsbuildinfo` and all existing `demo-preparation/` files were preserved.
- `py -0p` reports no installed Python runtimes, and `py -3.12 --version` reports no installed Python. `.venv-demo` remains absent; `.venv` was not changed.
- The current Python 3.12 security line is source-only. The last Python 3.12 release with Windows binary installers is 3.12.10. Download its official 64-bit full installer from [Python 3.12.10](https://www.python.org/downloads/release/python-31210/), install for the current user, and ensure the Python Launcher option is selected. Close and reopen PowerShell, then verify `py -3.12 --version` before running the venv commands above. Python's Windows documentation describes the full installer and per-user install options: [Using Python on Windows](https://docs.python.org/3.12/using/windows.html).
- Frontend `npm run typecheck` passes on the current branch after the narrow DTO/domain type corrections. Full `npm run lint` still fails (56 errors, 9 warnings); it also traverses generated Tauri output. The affected source files still have three React effect lint errors.
- Neither `demo-preparation/recording-data/` nor `demo-preparation/recording-knowledge/` existed at baseline. They were not created because Python 3.12 is missing.
- No process was listening on ports 3000, 8000, or 8001 at the time of inspection. No API or frontend was launched, seeded, or browser-verified in this follow-up.
