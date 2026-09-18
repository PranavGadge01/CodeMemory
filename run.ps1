# CodeMemory — One-Shot Launcher
# Usage: Right-click → "Run with PowerShell", or: pwsh -File run.ps1
# Works whether or not the venv is already activated.

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

Write-Host ""
Write-Host "  +--------------------------------------+" -ForegroundColor Cyan
Write-Host "  |        CodeMemory Launcher           |" -ForegroundColor Cyan
Write-Host "  +--------------------------------------+" -ForegroundColor Cyan
Write-Host ""

# ── 1. Locate / create virtual environment ────────────────────────────────────
$VenvDir      = Join-Path $Root ".venv"
$VenvPython   = Join-Path $VenvDir "Scripts\python.exe"
$VenvPip      = Join-Path $VenvDir "Scripts\pip.exe"
$VenvStreamlit= Join-Path $VenvDir "Scripts\streamlit.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "  [setup] Creating virtual environment..." -ForegroundColor Yellow
    python -m venv $VenvDir
    if (-not (Test-Path $VenvPython)) {
        Write-Error "Failed to create venv. Make sure Python 3.12+ is installed and on PATH."
    }
}

# ── 2. Install / sync dependencies (using venv pip directly) ─────────────────
Write-Host "  [setup] Installing / checking dependencies..." -ForegroundColor DarkGray
& $VenvPip install -e "$Root[dev]" --quiet --disable-pip-version-check

# Re-resolve streamlit path after install
$VenvStreamlit = Join-Path $VenvDir "Scripts\streamlit.exe"
if (-not (Test-Path $VenvStreamlit)) {
    Write-Error "streamlit not found after install. Check your pyproject.toml dependencies."
}

# ── 3. Launch Streamlit app ───────────────────────────────────────────────────
$AppEntry = Join-Path $Root "src\codememory\app\app.py"

Write-Host ""
Write-Host "  [app]   Starting CodeMemory -> http://localhost:8501" -ForegroundColor Green
Write-Host "          Press Ctrl+C to stop." -ForegroundColor DarkGray
Write-Host ""

& $VenvStreamlit run $AppEntry `
    --server.port 8501 `
    --server.headless false `
    --browser.gatherUsageStats false
