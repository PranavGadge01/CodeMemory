# CodeMemory project understanding

## Product overview

CodeMemory is a local-first DSA practice memory system. Its intended value is to preserve the path from failed attempt to accepted solution, then make that history searchable and useful for revision, analytics, pattern discovery, and learning recommendations. It is not a coding judge and does not execute submitted code.

The repository contains multiple product surfaces at different maturity levels:

- Next.js workspace and marketing/preview page in `frontend/`.
- FastAPI local API in `src/api/`, used by the Next.js workspace.
- Python domain/service layer in `src/codememory/` with a Rich CLI and Streamlit studio.
- Tauri desktop wrapper in `frontend/src-tauri/` that bundles a Python API sidecar.

The Next.js landing page explicitly labels its data as example data. The actual workspace reads data through the API. The Settings page says file import, index rebuild, and data deletion are not exposed there. Import exists in the Python CLI and Streamlit surface. This split matters to a buyer: the current web workspace does not itself demonstrate the whole ingest-to-learning loop.

## Architecture

```text
Next.js workspace ──HTTP──> FastAPI local API ──> CodeMemoryService
                                      │                    │
                                      │                    ├── DuckDB relational index
                                      │                    ├── Parquet analytical/cache files
                                      │                    └── Markdown knowledge directory
                                      └── LeetCode routes

Streamlit studio / Rich CLI ────────────────> CodeMemoryService
Tauri desktop shell ──sidecar lifecycle─────> FastAPI executable
```

`CodeMemoryService` coordinates ingestion, account scoping, analytics, revision scoring, semantic memory, AI/evidence features, export, and repository abstractions. Domain entities are Pydantic models: Problem → Attempts → Submissions, with notes and optional analysis. Composite storage synchronizes DuckDB, Parquet, and readable files under the knowledge directory. There is no standalone database server or queue service.

## User-facing feature inventory

| Feature | Current surface | Runtime finding |
|---|---|---|
| Product overview | `/` | Visually verified. Marks charts/story “example data”; not user history. |
| Local workspace | `/dashboard` | Loaded from configured API with zero records; evolution card is separately illustrative. |
| Problem history | `/problems` | Page and zero-state verified. Detail path unavailable without records. |
| Submission log | `/submissions` | Failed at runtime: `filterOptions` undefined and `SubmissionsBrowser` reads `statusCounts`. |
| Revision queue | `/revision` | Empty queue loaded; scoring/mark-reviewed could not be exercised. |
| Search | `/search` | Query submission and no-results state verified. No corpus to prove positive retrieval. |
| Analytics | `/analytics` | Core empty metrics loaded. Four learning/insight cards returned HTTP 404. |
| Knowledge graph | `/knowledge` | Empty graph state loaded. Node interactions unavailable without nodes. |
| Preferences | `/settings` | Settings loaded; no changes submitted, so persistence is untested. |
| LeetCode connection | `/connect`, Settings | Disconnected status/form verified read-only; no account connected. |
| Import | CLI / Streamlit | Source/tests exist; not runtime tested. No import endpoint/screen in current Next UI. |
| AI / explainable learning | API routes and UI cards | Backend source exists; visible analytics cards returned 404. Other analyses not exercised. |
| Personal memory / export | CLI/services | Source, docs, tests exist; not runtime tested. |
| CLI / Streamlit studio | `codememory`, `run.ps1` | Blocked: repository venv points to a missing Python 3.13 runtime. |
| Desktop packaging | Tauri | Config/spec inspected; desktop app not run. Packaged API executable returned immediately. |

## Roles and permissions

There is no application login or role/permission matrix in the current local product. `/auth/sign-in` says “No account needed” and links directly to the workspace. The model is a single local workspace with optional LeetCode account identities. Backend services apply active-account filtering to LeetCode-sourced submissions; this is data scoping, not authorization between app roles. Do not pitch admin/team/multi-user access as implemented.

## External dependencies and services

- Python 3.12+ (per `pyproject.toml`), project dependencies installed in an environment.
- Node/npm for the Next frontend; package specifies Next.js 16 / React 19.
- Local FastAPI process, default port 8000; frontend example config points to 8001.
- DuckDB, Polars, PyArrow, and local filesystem; no database daemon required.
- LeetCode public GraphQL/network access for public profile/recent accepted submission sync. Public sync omits source code/runtime/memory and is not complete history. Optional authenticated sync requires session/CSRF credentials and local credential storage; never show or enter them during recording.
- Optional OpenAI API key or local OpenAI-compatible Qwen endpoint. Heuristic provider runs offline. `.env.example` names `OPENAI_API_KEY`, `AI_ENABLED`, `EMBEDDING_PROVIDER`, `CODEMEMORY_*`, and remote-catalog settings. Qwen settings include endpoint/model/timeout variables. Do not inspect or display existing `.env` or `frontend/.env.local` values.
- No Redis, queue, email, or realtime service found. Optional LeetCode autosync is a service-owned thread, disabled unless enabled.

## Feature-to-implementation map

| Capability | Main implementation |
|---|---|
| Domain entities and enums | `src/codememory/domain/models.py`, `enums.py` |
| Service orchestration | `src/codememory/core/service.py` |
| Composite / DuckDB / Parquet / Markdown | `src/codememory/storage/composite_repository.py`, `duckdb_repository.py`, `parquet_repository.py`, `fs_repository.py` |
| Import parsing and deduplication | `src/codememory/ingestion/parsers.py`, `importer.py`, `src/codememory/connectors/leetcode/parser.py`, `mapper.py`, `importer.py` |
| Analytics and revision | `src/codememory/analytics/analytics_service.py`, `src/codememory/revision/revision_service.py` |
| Search and semantic memory | `src/codememory/search/`, `src/codememory/memory/` |
| AI and evidence grounding | `src/codememory/ai/`, `src/api/routes/insights.py`, `learning.py` |
| Knowledge graph and patterns | `src/codememory/graph/`, `src/codememory/patterns/` |
| Export | `src/codememory/exporters/knowledge_exporter.py` |
| API routes and DTOs | `src/api/routes/`, `src/api/schemas/`, `src/api/app.py` |
| Current frontend routes | `frontend/app/`, `frontend/components/app/` |
| Frontend API transport/mapping | `frontend/lib/api/client.ts`, `resources.ts`, `mappers.ts` |
| Landing example data | `frontend/lib/mock/`, `frontend/lib/data.ts`, `frontend/app/page.tsx` |
| Streamlit studio | `src/codememory/app/`, `src/codememory/app/pages/` |
| CLI and sample seed | `src/codememory/cli/main.py`, `scripts/seed_data.py` |
| Tauri lifecycle/build | `frontend/src-tauri/`, `frontend/package.json`, `backend/codememory-api.spec` |

The Streamlit sidebar source declares 13 destinations: Dashboard, Problems Directory, Problem Detail, Solution View, Revision Queue, Ask CodeMemory, My Patterns, Knowledge Graph, Deep Analytics, Data Import, Knowledge Export, Global Search, and Settings. This is a source inventory, not proof each page currently runs. Its “Seed Sample Data” control calls the seed against the default service path; do not use it in this checkout during demo setup.

## Uncertainties and blockers

1. Browser read requests reached a configured local API, but its process owner and backing data path could not be independently verified. The packaged API executable exited without logs. Treat this as API compatibility evidence, not proof of a clean startup.
2. The current API-backed dataset has zero indexed problems/submissions. Positive ingest → stored submission → analytics/revision/search was not demonstrated.
3. Frontend/API compatibility is visibly incomplete: analytics insight/learning cards returned 404 and submissions crashed on missing `filterOptions`.
4. `npm run typecheck` fails on numerous DTO naming/type mismatches. ESLint reports 57 errors and 10 warnings, including generated Tauri output.
5. Python runtime and tests are blocked; see reports 03 and 08.
6. Default CLI/Streamlit constructors use relative `data`/`knowledge` paths. Do not run seed/import or `run.ps1` in this checkout until an isolated working directory is established.
