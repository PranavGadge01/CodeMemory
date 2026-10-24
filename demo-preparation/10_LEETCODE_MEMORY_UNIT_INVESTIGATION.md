# LeetCode Memory-Unit Investigation

## Status

The authenticated LeetCode sync now normalizes memory at the ingestion boundary through `normalize_leetcode_memory`. It is used for both new submissions and duplicate records whose code is enriched. The generic `parse_memory` behavior remains unchanged. Historical records were not changed, and no credentials or network requests were used during this follow-up.

The raw GraphQL `submissionDetails.memory` unit remains **unverified**. The conversion below is an empirical source-specific normalization supported by one paired UI/API record, not a claim about LeetCode's formal upstream contract.

## Paired evidence supplied

The matching Find Peak Element submission was submitted September 21, 2026 at 13:52:

| Source | Memory | Runtime | Other details |
|---|---:|---:|---|
| LeetCode submission details | 44.19 MB | 0 ms | Accepted |
| CodeMemory API | `memoryMb: 44192000.0` | `runtimeMs: null` | `sourceProvider: leetcode`; ID `leetcode_2148432831` |

`44,192,000 / 1,000,000 = 44.192`, which rounds to the UI's 44.19 MB. This supports normalizing numeric values from this authenticated detail path by dividing by 1,000,000. It does not independently establish the raw GraphQL unit or prove that every historical numeric value originated from this representation.

## Source trace

- `src/codememory/connectors/leetcode/authenticated_client.py` requests `code`, `runtime`, `memory`, `timestamp`, `statusCode`, language, and question fields for one submission ID. It returns `memory` unchanged and requests no unit metadata.
- `src/codememory/connectors/leetcode/auth_sync.py` applies the source-specific normalizer when authenticated submission details provide code. The normalized value is assigned to a new record and reused when the existing record is updated with newly fetched code. Missing/unsupported detail values do not replace a stored metric during duplicate enrichment.
- The public profile sync in `src/codememory/connectors/leetcode/sync.py` documents runtime and memory as unavailable and passes the normalized record's absent values through; it does not ingest this GraphQL detail field. LeetCode JSON/CSV files go through `src/codememory/connectors/leetcode/importer.py` and `NormalizedSubmissionRecord`, so their values retain the generic `parse_memory` behavior. This fix is intentionally limited to authenticated `submissionDetails` ingestion.
- `src/codememory/domain/import_schema.py::normalize_leetcode_memory` handles numeric `int`/`float` values using the observed decimal-million scale; accepts explicitly unit-tagged strings by calling the unchanged generic parser; and returns `None` for missing values, untagged numeric strings, booleans, negative/non-finite numbers, and unsupported representations.
- `src/codememory/domain/import_schema.py::parse_memory` retains its previous behavior, including returning numeric values unchanged as MB and parsing explicitly tagged units using its existing conversions.
- DuckDB persistence and the API return the stored number without another conversion; the frontend labels the value in MB.
- Other inspected fixtures did not provide another paired LeetCode UI/API example. Existing mock numeric detail values are test inputs, not independent upstream evidence.

## Implementation and tests

Changed implementation and test files:

1. `src/codememory/domain/import_schema.py` — source-specific normalizer; generic parser unchanged.
2. `src/codememory/connectors/leetcode/auth_sync.py` — one normalizer call shared by insert and duplicate code-enrichment handling.
3. `tests/test_validation.py` — paired numeric example, unchanged generic numeric semantics, missing/null values, explicit tagged strings, and rejected representations.
4. `tests/test_leetcode_authenticated.py` — authenticated insert and duplicate-update assertions use the paired numeric input, and a subsequent missing-memory update preserves the normalized stored value.

### Python environment and Polars diagnosis

- `pyproject.toml` declares `polars>=1.0.0`; this is a lower bound, not a fixed pin. `uv.lock` resolves Polars and `polars-runtime-32` to **1.44.2** and includes Windows x64/ARM64 wheels.
- The repository's documented install command is `pip install -e ".[dev]"` (README and `02_RUN_AND_TEST_GUIDE.md`). pip does not consume `uv.lock`; it follows the open-ended project requirement. `.venv-demo` has the pip `INSTALLER` marker and contains **polars 2.0.0** plus **polars-runtime-32 2.0.0**. The exact historical pip resolver log is not retained, but the documented command and package metadata explain why the lockfile version was not applied.
- The runtime's CPU feature declaration asks Polars' `_cpu_check.py` to check `sse3`. In this environment, Python reports `sysconfig.get_platform() == "win-amd64"` but `platform.machine()` is empty. Polars consequently sets `_SUPPORTS_CPUID=False` and `_read_cpu_flags()` returns `{}`; `check_cpu_flags()` then reports `sse3` as an *unknown flag*. This is an architecture-detection failure, not evidence that the physical CPU lacks SSE3. Do not bypass it with `POLARS_SKIP_CPU_CHECK` or force a runtime package; that could hide an actual compatibility issue.
- No `uv` executable is installed. The repository-local `tmp/uv-cache` contains no package artifacts, and pip's cache contains no Polars wheel. Therefore a new lock-synchronized environment could not be assembled offline here. A compatible separate environment is recommended only after a trusted `uv` executable and the locked wheels are available offline, or on a host where Python reports a supported CPU architecture.

### Validation results (Python 3.12.10 in `.venv-demo`)

- `python -m pytest -q tests/test_validation.py`: **8 passed**.
- `python -m py_compile src/codememory/domain/import_schema.py src/codememory/connectors/leetcode/auth_sync.py tests/test_validation.py tests/test_leetcode_authenticated.py`: **passed**.
- `python -m pytest -q tests/test_leetcode_authenticated.py`: **blocked during collection** when the connector imports storage and Polars raises `RuntimeError: unknown feature flag: 'sse3'`; **0 test cases ran**.
- Full `python -m pytest -q`: **blocked during collection** with the same failure across 47 modules; pytest reported 117 collected items, but the errored modules did not complete collection. Pytest also reported a Windows `PermissionError` while cleaning a temporary directory at process exit; no project data was targeted.

The focused normalizer tests pass. The authenticated insert/update tests exist and statically call the shared normalizer, but their storage/integration behavior remains **not runtime-verified**. No dependency version or CPU-check setting was changed.

### Safe separate-environment command (only when offline artifacts are present)

This keeps `.venv` and `.venv-demo` untouched and asks uv to honor the checked-in lock without contacting a package index. It was **not run** because uv and the lock wheels are unavailable locally:

```powershell
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { throw "Provide the trusted uv executable first; do not install over the network in an offline environment." }
$machine = & .\.venv-demo\Scripts\python.exe -c "import platform; print(platform.machine().lower())"
if ($machine -notin @('amd64', 'x86_64', 'x64')) { throw "Python cannot identify an x86 CPU for Polars; use a compatible test host before creating the test environment." }
$env:UV_PROJECT_ENVIRONMENT = Join-Path $PWD '.venv-leetcode-locked'
if (Test-Path -LiteralPath $env:UV_PROJECT_ENVIRONMENT) { throw "Choose a new environment path; preserve existing work." }
uv sync --locked --offline --extra dev
& .\.venv-leetcode-locked\Scripts\python.exe -c "import platform; print(platform.machine()); import polars; print(polars.__version__)"
& .\.venv-leetcode-locked\Scripts\python.exe -m pytest -q tests/test_validation.py tests/test_leetcode_authenticated.py
```

Proceed with tests only if uv reports a successful offline sync and Polars imports without bypassing its feature check. If the lock artifacts are unavailable offline, stop and obtain an approved wheelhouse or use a compatible test host; do not modify dependency pins to force a result.

## Historical data

No stored rows were changed. Do not mass-divide all historical LeetCode memory values: the paired example does not classify every record's origin or representation. A future repair should first stop the API, take a restorable backup of the exact active data and knowledge roots, inspect rows by provider/account without exposing code or credentials, validate every proposed value against independent upstream evidence, and update a copy in a transaction. A fresh isolated sync is preferable for validating the new normalization before considering any historical repair.
