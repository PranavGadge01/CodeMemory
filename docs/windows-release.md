# Windows desktop and release guide

CodeMemory ships a static Next.js frontend in Tauri 2 and a windowless
PyInstaller FastAPI sidecar. The local API binds to `127.0.0.1:8000`.
The website is a separate static build. CLI and developer studio remain available.

## Development

Prerequisites: Python 3.12/3.13, Node 22.13+ and npm, Rust stable, Visual Studio
Build Tools with Desktop development with C++, Windows SDK, and WebView2.
Run from the repository root in PowerShell:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e '.[dev]'
npm --prefix frontend ci
npm --prefix website ci
```

For browser development, run the API and frontend in separate terminals:

```powershell
.venv/Scripts/python.exe -m api.app
npm --prefix frontend run dev
```

`NEXT_PUBLIC_API_URL` defaults to `http://127.0.0.1:8000/api/v1`; it is inlined
at build time. Desktop production requires that loopback URL. Development
uses the repository's `data/` and `knowledge/` by default.

For the native development shell, stop any separate API process, build its
sidecar, then start Tauri (it launches the frontend itself):

```powershell
npm --prefix frontend run sidecar:build
Set-Location frontend
npm run tauri dev
```

## Build and verify

From the repository root:

```powershell
node scripts/sync-version.mjs --check
New-Item -ItemType Directory -Force build/tests | Out-Null
Push-Location build/tests
../../.venv/Scripts/python.exe -m pytest ../../tests
../../.venv/Scripts/python.exe -m pytest ../../tests/test_productization_ownership.py ../../tests/test_runtime_migration.py
Pop-Location
npm --prefix frontend run typecheck
npm --prefix frontend run build
Push-Location frontend/src-tauri
cargo check
Pop-Location
npm --prefix website run typecheck
npm --prefix website run build
npm --prefix website test
npm --prefix frontend run test:e2e
Push-Location frontend
npm run tauri build
Pop-Location
./scripts/collect-release.ps1
```

Backend tests run in an isolated working directory because some older fixtures
use relative export paths even with an in-memory database. The default test
configuration excludes tests marked `live`. Browser regressions use Edge and
real API/storage with a stubbed remote LeetCode transport. They require ports
8000, 4173 and 4174 to be free. They do not validate a live LeetCode session.

`npm run tauri build` runs the static frontend build and PyInstaller automatically.
The authoritative spec is `backend/codememory-api.spec`; the root-level generated
spec is ignored. Output:

```text
frontend/out/                                      static frontend
dist/codememory-api.exe                            bundled backend
frontend/src-tauri/target/release/bundle/msi/       MSI installer
frontend/src-tauri/target/release/bundle/nsis/      NSIS installer
build/release/                                    copied installers + SHA256SUMS.txt
```

Static frontend assets are embedded in the Tauri application. The sidecar is a
bundle resource; Tauri may place it under `_up_/_up_/dist/`. Both resource layouts
are recognized. Generated installers and all runtime data stay out of Git.

## Runtime and installation behavior

Launch waits up to 90 seconds for the newly started sidecar's health identity.
The child has no console window. A port conflict or startup failure is reported
in a native dialog. Closing the GUI terminates the process tree; a Windows Job
Object also terminates children if the parent crashes. The app never kills an
unrelated process merely because it owns port 8000.

First launch shows one intro, then username entry and public sync. A configured
account goes directly to Dashboard. Optional credentials are entered in Settings.
Switch account starts a new frontend document so prior account state is cleared.
Disconnect revokes that account's credentials and returns to Connect LeetCode;
imported history stays stored. See [data migration](data-migration.md).

Close CodeMemory before updating. Use the same Windows user for upgrade testing
so the OS keyring remains accessible. Back up the complete runtime directory;
do not export decrypted credentials. Validate fresh and existing-data launches,
public/authenticated sync, details/code, search, revision, analytics, account
switching, close/reopen, and persistence. A same-version reinstall is not proof
of an upgrade from a previously published version.

## Version and publication

`release.json` is the version authority. Change it and run
`node scripts/sync-version.mjs`; review the generated manifest/version changes.
`--check` fails on drift. CI offers a manual Windows build workflow that uploads
verified installers as build artifacts without publishing a release.

The repository is `https://github.com/PranavGadge01/CodeMemory`. After final review
and an explicitly requested source commit/tag, publish the tested artifacts to
GitHub Releases as `v<version>` with these exact names:

```text
CodeMemory_<version>_x64-setup.exe
CodeMemory_<version>_x64_en-US.msi
SHA256SUMS.txt
```

Verify both download URLs and checksums, then set `published: true` in
`release.json` and rebuild/deploy the website. No source commit, tag, push or
release publication is performed by the build scripts. The current repository
has no published release; default website buttons are disabled until one exists.

For a complete self-hosted static download site using locally built installers:

```powershell
./scripts/collect-release.ps1
$env:CODEMEMORY_RELEASE_DIR = (Resolve-Path build/release).Path
npm --prefix website run build
npm --prefix website test
Remove-Item Env:CODEMEMORY_RELEASE_DIR
npm --prefix website run preview
```

Deploy `website/out/` including its generated `releases/v<version>/` directory.
These installer files remain generated artifacts, never source files.
Installers are unsigned unless release signing is separately configured; a
clean Windows machine may show publisher/SmartScreen prompts. WebView2 may
require an internet connection when it is not already installed.
