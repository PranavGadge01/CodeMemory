# Demo data and preparation

## Test identity and records

Use only synthetic records. Two supported preparation choices are described below; choose one per fresh profile. The richer CLI seed creates 22 classic DSA problems. For an import-first story, the repository test fixture contains six synthetic LeetCode-format submissions across familiar problems. Neither creates a login account. Do not connect a real LeetCode profile or import anyone’s export in the recording.

| Item | Plan |
|---|---|
| App user | No account required; current product has no user roles. |
| Dataset | Choose synthetic `seed_sample_data()` (22 problems) or `tests/fixtures/leetcode/sample_leetcode.json` (6 sample submissions). |
| Integration | Keep LeetCode disconnected; choose offline heuristic analysis. |
| Paths | `demo-preparation/recording-data/`, `recording-knowledge/`, and `recording-data/codememory-demo.duckdb`. |
| Repeatability | Seed once into a fresh dedicated folder. For another take, choose a new folder name in seed and API commands. |
| Cleanup | Stop services and retain synthetic data. Remove only after manually verifying these exact folders contain only this demo. No cleanup was done. |

## Safe seed setup

1. Install/verify Python 3.12 and `.venv-demo` using `02_RUN_AND_TEST_GUIDE.md`.
2. From repo root, confirm target folders do not exist or are empty. If anything unexpected is present, stop and choose new names.
3. Run the explicit isolated Python seed snippet in `02_RUN_AND_TEST_GUIDE.md` exactly once. It passes `base_dir`, `knowledge_dir`, and `db_path` to `CodeMemoryService`, avoiding project `data/` and `knowledge/`.
4. Start FastAPI with those same paths. Confirm API health before opening the workspace.
5. Inspect positive record counts before recording.

Do not use `codememory seed` or `run.ps1` in this checkout for the demo: the CLI/Streamlit service uses default relative directories, unlike the API environment configuration. The seed is not verified idempotent.

## Preparation verification sequence

After seeding and starting both services, verify in the browser:

1. Dashboard has nonzero counts; example evolution remains labeled illustrative.
2. `/problems` shows seeded records. Search `Two Sum`, open its row, and confirm attempts/submissions match the record.
3. `/submissions` loads without a Next error and shows failed/accepted records when present.
4. `/revision` returns queue rows and score explanation. Do not click reviewed until persistence is separately verified.
5. `/search` query a phrase actually present in seeded notes/code, such as `Hash Table`.
6. `/knowledge` shows graph nodes/edges; select a node without changing data.
7. `/analytics` loads metrics. All learning/insight cards must return without 404 before inclusion.
8. Settings shows LeetCode disconnected. Do not change a preference unless persistence is tested against the isolated folder.

### Import-first alternative for the legacy Streamlit studio

The Streamlit workflow contains a Data Import page. Start it with `demo-preparation/streamlit-profile` as the working directory using the isolated command in `02_RUN_AND_TEST_GUIDE.md`; this keeps default relative storage out of repo `data/`. In **Data Import**, choose **LeetCode Export Dataset (JSON / CSV)**, upload the test fixture `tests/fixtures/leetcode/sample_leetcode.json` (six synthetic records), inspect **LeetCode Normalization & Validation Preview**, and click **Confirm & Import LeetCode Dataset** once. Then verify the import result and browse those records in the studio. This writes synthetic data only to the isolated profile.

For a shared Next/API walkthrough, stop Streamlit first, then point API `CODEMEMORY_DATA_DIR`, `CODEMEMORY_KNOWLEDGE_DIR`, and `CODEMEMORY_DB_PATH` at the matching profile directories. Do not start two independent DuckDB processes on that file simultaneously. The six-record fixture and 22-problem seed are alternatives; do not seed and import into the same profile unless you intentionally want both datasets.

This is a test plan, not a claim that positive flows passed. Current runtime had no verified synthetic dataset; submissions/analytics issues were observed.

## External integration limits

- Public LeetCode sync needs Internet and a real public username. It returns recent bounded accepted submissions and omits source code/runtime/memory; no demo username is provided. Do not invent one or claim full history.
- Authenticated full-history sync needs session and CSRF values in the vault. Never put them in a recording or notes. Not needed for a synthetic demo.
- `OPENAI_API_KEY` is optional and must never be printed. This plan sets `AI_PROVIDER=heuristic`; Qwen needs a separate local model server. Analytics cards returned 404 in the observed API regardless of provider.
- No email, queue, cache daemon, or realtime service was identified.

## Readiness follow-up — 2026-10-14

- The existing `demo-preparation/runtime-data/` directory still contains `accounts/`, `parquet/`, `codememory-demo.duckdb` (12,288 bytes), and `codememory-demo.duckdb.wal` (2,835 bytes). Only names and file metadata were checked; the files were not opened, moved, deleted, or modified. Their contents/counts remain unknown and they are not the demo dataset.
- `demo-preparation/recording-data/` and `demo-preparation/recording-knowledge/` were confirmed absent and left absent. No seed data or test account was created because Python 3.12 is unavailable.
- The next seed should use those fresh explicit paths only after Python is installed and before the source API is started. Do not infer any problem or submission count from the untouched runtime-data database.
