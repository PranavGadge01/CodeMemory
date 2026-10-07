# CodeMemory Performance Audit

**Type:** read-only performance audit. **No source, config, data, schema, test, or package files were modified.**
**Repository:** `C:\Users\shrey\OneDrive\Desktop\Shrey\MERN\CodeMemory`
**Date:** 2026-10-07
**Symptom under investigation:** "The UI loads with a small but noticeable delay."

## How this audit was performed

- Static tracing of the real runtime (Tauri shell, Next.js static export, FastAPI, `CodeMemoryService`, DuckDB/Parquet/Markdown, AI providers).
- Direct measurement of the storage primitives the API depends on, using a **read-only** DuckDB connection (`duckdb.connect(..., read_only=True)`) plus **read-only** Python imports. No service was constructed against the live database, because `CodeMemoryService.__init__` runs DDL (`CREATE TABLE IF NOT EXISTS` / `ALTER TABLE ADD COLUMN IF NOT EXISTS`) and a hash-repair pass, which would write to the DB file.
- No server was running during the audit (`Get-NetTCPConnection` showed nothing on 8000/3000; `GET /api/v1/health` refused the connection), so **no endpoint was timed end to end**. Every per-endpoint figure in this report is therefore *computed* from (a) measured storage primitives and (b) call counts verified in code. Those figures are labelled **INFERRED** and the exact end-to-end numbers remain a measurement gap.
- `git status --porcelain` was empty before and after the audit.

Every claim below carries a measurement label:

| Label | Meaning |
|---|---|
| **MEASURED** | Directly observed on this machine during the audit. |
| **INFERRED** | Computed from measured primitives plus code-verified call counts/structure. |
| **SUSPECTED** | Architectural risk that needs a live profiler to confirm magnitude. |
| **UNKNOWN** | Not measurable with the available (read-only, no-server) tooling. |

---

## 1. Executive Summary

- **The UI is not render-bound or bundle-bound. It is backend-scan-bound.** The shell paints immediately from the static export; the delay is the time the FastAPI process spends re-reading the *entire* dataset, over and over, for a handful of endpoints. **MEASURED / INFERRED**
- **`storage.list_all()` costs ~200 ms warm and ~690 ms cold, and it is not cached.** One call issues **299 SQL statements** (1 problems query + 2 per problem + 1 per attempt) because `DuckDBStorage._build_problem_from_row` loads attempts, then submissions *per attempt*, then notes *per problem*. **MEASURED** (`duckdb_repository.py:474-572`)
- **The dashboard and revision endpoints are effectively O(N^2).** `RevisionService.get_revision_queue` expands the whole dataset once, then calls `get_problem_priority()` per problem, and that method calls `analytics.get_topic_statistics()` — which expands the whole dataset *again*. With the 35 account-scoped problems in this DB that is ~36 full expansions ≈ **7.3 s of work** on one request, and `/dashboard` triggers it. **INFERRED (HIGH confidence on the pattern, MEDIUM on magnitude)**
- **The analytics page fans out 5 independent requests, each doing 2–10 full-dataset expansions, and they cannot run in parallel** because every query serialises on one process-wide DuckDB connection guard. Parallel client requests do not shorten the total. **MEASURED (lock design) / INFERRED (totals)**
- **The Problems / Submissions pages issue an HTTP-level N+1:** after a list call they fetch **one `GET /problems/{slug}` per problem** (~52 on this dataset), each returning full submission code; the effect re-runs on *every* filter/search change. **MEASURED (code) / INFERRED (counts)**
- **The app shell calls `GET /health` on every page**, and `/health` itself expands the dataset 2–3 times (problem count + search + first-call memory index). The Tauri readiness probe also polls `/health` every 500 ms while booting. **MEASURED (code)**
- **AI is not on the critical path today.** No `.env` exists, `AI_PROVIDER` is unset and `OPENAI_API_KEY` is unset, so the provider is the offline `HeuristicAIProvider`; the AI layer adds no network latency. It becomes a real risk only if `AI_PROVIDER=qwen|openai` is set. **MEASURED (env) / SUSPECTED (risk)**
- **Cold start has two non-backend costs:** the sidecar is a PyInstaller *onefile* exe (extract-to-temp on every launch), and the Tauri `setup` hook blocks synchronously on a health-check loop (500 ms poll, 30 s timeout) before the app is considered ready. **MEASURED (code) / UNKNOWN (magnitude; no built sidecar in `dist/`)**

---

## 2. Architecture (as actually implemented)

The README describes a Streamlit UI. **That is not the runtime.** The real UI is a Next.js static export inside a Tauri desktop shell talking to a local FastAPI sidecar.

```
 Desktop shell (Tauri 2.11 / Rust)
   frontend/src-tauri/src/main.rs -> lib.rs::run()
     setup(): sidecar::start()  [BLOCKING loop: GET /api/v1/health every 500ms, 30s timeout]
       spawn: dist/codememory-api.exe --host 127.0.0.1 --port 8000   (PyInstaller onefile)
     window (1440x900) -> frontendDist "../out"   (static Next.js export served from disk)
   run.ps1 / run.bat  = legacy Streamlit launcher (not the desktop path)

 Frontend (Next.js 16.3.5 / React 19.2.8, output: "export" => fully client-rendered routes)
   app/layout.tsx            root: SettingsProvider + ThemeProvider + no-flash theme script
   app/(app)/layout.tsx      AppShell (sidebar + topbar); sidebar mounts MemoryStatus -> GET /health
   app/(app)/{dashboard,analytics,problems,submissions,knowledge,revision,search,settings}
   Every page = "use client" + useState machine + useEffect(fetch) + skeleton
   lib/api/client.ts -> fetch(API_BASE_URL) with cache:"no-store"; no retry, no SWR/React Query
   lib/api/resources.ts -> 1 function per endpoint; lib/api/mappers.ts -> DTO->domain mapping

 API (FastAPI 0.141.1, uvicorn, src/api)
   app.py::create_app() -> routers under /api/v1 (health, dashboard, problems, submissions,
       analytics, knowledge, revision, leetcode, search, insights, learning, settings)
   lifespan(): CodeMemoryService(...) constructed ONCE, stored on app.state; closed on shutdown
   dependencies.get_service() returns that singleton
   ALL route handlers are sync `def` (run in the threadpool), not `async def`
   CORSMiddleware; exception handlers; no other middleware

 Core (src/codememory/core/service.py, 1168 lines)
   CodeMemoryService composes: CompositeStorage, AnalyticsService, SearchService, PatternAnalyzer,
   RevisionService, InsightsGenerator, AI provider, AICodeAnalyzer, EvolutionService, MemoryService,
   MemoryEngineService, EvidenceBuilder, InsightService, KnowledgeGraphBuilder
   property `active_account` -> self.leetcode._account_service.get_connection("LeetCode")  (lazy, JSON file)
   property `leetcode` / `autosync` -> lazily built (autosync thread only starts if used)

 Storage (src/codememory/storage)
   CompositeStorage -> DuckDBStorage (CANONICAL, read path) 
                     + FilesystemStorage(knowledge/ markdown, write-through export)
                     + ParquetStorage(data/parquet, write-through export)
   One pooled DuckDB connection per db_path, guarded by a process-wide RLock (_lock_for)

 AI (src/codememory/ai)
   get_ai_provider(): qwen | openai | heuristic; default = heuristic (no env) 
   EvidenceBuilder -> InsightService -> provider -> EvidenceValidator -> GroundedInsight
   AICodeAnalyzer: in-memory + parquet cache of past analyses (0 cached in this DB)
---

## 3. Baseline Measurements

### 3.1 Dataset and storage primitives (MEASURED)

| Metric | Value | How |
|---|---:|---|
| Problems in DuckDB | 52 | `SELECT count(1) FROM problems` (read-only) |
| Attempts | 194 | read-only query |
| Submissions | 89 | read-only query |
| Notes | 0 | read-only query |
| Total submission code | 21,286 chars (max 1,096) | read-only query |
| Submissions carrying complexity | 0 attempts have `time_complexity` | read-only query |
| Accounts present | `shrey_sawant` (66 subs), `JWSztSMf2l` (23 subs) | read-only query |
| Problems scoped to active account | 35 | read-only query |
| `data/codememory.duckdb` size | 5,388 KB | filesystem |
| Parquet tier | 3 files, ~12 KB total | filesystem |
| Knowledge base | 150 dirs / 579 files | filesystem |
| DuckDB `connect(read_only=True)` | **20.8 ms** | `time.perf_counter()` |
| `storage.list_all()` — 299 statements | **first 693 ms; steady 190–217 ms** | faithful re-implementation incl. Pydantic construction |
| Same expansion, raw tuples only | first 1349 ms; steady 203–219 ms | read-only measurement |
| 299 trivial `SELECT 1` statements | 36.8 ms | isolates per-statement overhead |
| One `SELECT * FROM submissions` (89 rows) | 0.066 ms avg | isolates query cost |
| Single-problem expansion | median 2.07 ms, p95 5.40 ms | per-problem read-only loop |
| `import codememory.domain.models` | 275 ms | `time.perf_counter()` |
| `import codememory.core.service` | **836 ms** | `time.perf_counter()` |
| `import api.app` | **987 ms** | `time.perf_counter()` |
| `import uvicorn` | 78 ms | `time.perf_counter()` |

**Interpretation.** The 299-statement expansion costs ~200 ms while the same *number* of trivial statements costs 37 ms, so the cost is dominated by per-statement planning/execution on the real tables plus Python object construction — **not** by raw row volume (the whole submissions table scans in 0.066 ms). The N+1 shape, not the data size, is the problem: it scales with *problem count*, so it degrades as the user's history grows.

### 3.2 Frontend bundle (MEASURED, from the existing `frontend/out` export)

| Metric | Value |
|---|---:|
| JS chunks in `out/_next` | 26 files / **968.1 KB** total (uncompressed) |
| CSS | 53.7 KB |
| JS referenced by `dashboard.html` | ~656.7 KB (incl. a 110 KB `noModule` legacy fallback) |
| Fonts preloaded | Geist 68 KB + Geist Mono 69.7 KB |

### 3.3 End-to-end table (cold vs warm)

| Metric | Cold | Warm | Status |
|---|---:|---:|---|
| App startup (Tauri window usable) | Not measured | Not measured | **UNKNOWN** (no release build present) |
| Sidecar first-health-ready | Not measured | Not measured | **UNKNOWN** (no built sidecar in `dist/`) |
| Backend module import | 987 ms | n/a (process-global) | **MEASURED** |
| First UI paint (shell) | Not measured | Not measured | **UNKNOWN** (no browser profiling available) |
| `storage.list_all()` | 693 ms | ~200 ms | **MEASURED** |
| `/analytics` | ~1.0 s | ~1.0 s | **INFERRED** (5 expansions) |
| `/dashboard` | ~8.7 s | ~8.7 s | **INFERRED** (7 expansions + revision queue) |
| `/revision` | ~7.3 s | ~7.3 s | **INFERRED** (36 expansions) |
| `/insights` | ~1.7 s | ~1.5 s | **INFERRED** (7 expansions + ≤10 problem lookups) |
| `/learning/profile` | ~2.2 s | ~2.0 s | **INFERRED** (~10 expansions) |
| `/learning/recommendations` | ~0.6 s | ~0.4 s | **INFERRED** (2 expansions) |
| `/learning/roadmap` | ~0.6 s | ~0.4 s | **INFERRED** (2 expansions) |
| `/health` | ~0.9 s | ~0.4 s | **INFERRED** (2–3 expansions) |
| `/problems` (list) | ~0.9 s | ~0.2 s | **INFERRED** (1 expansion) |
| `/problems/{slug}` | ~7 ms | ~2 ms | **MEASURED** (single-problem expansion) |
| Total API waterfall, Analytics page | ~5.3 s | ~5.3 s | **INFERRED** |
| Total API waterfall, Dashboard | ~9.1 s | ~9.1 s | **INFERRED** |
| AI latency | 0 (heuristic) | 0 (heuristic) | **MEASURED** (no env config) |

Warm/cold here means "DuckDB file already paged in / first read after process start". The 3x cold penalty on the first expansion is the file being read from disk.

---

## 4. Frontend Findings

### 4.1 There is no server rendering of data — every route is a client fetch + skeleton

`next.config.ts` sets `output: "export"`. All pages are `"use client"` with a `useState` machine and `useEffect(fetch)`. The static export does pre-render the **shell** (sidebar/topbar markup is present in `out/dashboard.html`), so first paint is fast, but **no page data exists until after hydration + a fetch**. Answers to the Phase-2 framing: the app is **(C) skeleton-driven** at the page level, and **(D) multi-request before usable** on Analytics/Problems/Submissions/Knowledge.

### 4.2 Waterfall #1 — Analytics page (2 stages, 5 requests)

`frontend/app/(app)/analytics/page.tsx:31-42` fetches `getAnalytics("week")` and renders **nothing but the page skeleton** until it resolves (`if (state.status !== "success") return <AnalyticsPending .../>`). Only then do four self-fetching cards mount, each firing its own request:

| Card | File | Endpoint |
|---|---|---|
| `CollectiveInsightsCard` | `components/app/analytics/collective-insights-card.tsx:162` | `GET /learning/profile` |
| `GroundedInsightCard` | `components/app/grounded-insight-card.tsx:38` | `GET /insights` |
| `NextProblemsCard` | `components/app/analytics/next-problems-card.tsx:126` | `GET /learning/recommendations` |
| `PersonalizedRoadmapCard` | `components/app/analytics/personalized-roadmap-card.tsx:234` | `GET /learning/roadmap` |

So the analytics data is fetched as `A -> {B,C,D,E}`. The first wave alone is ~1.0 s of backend scan time plus one round trip; the second wave adds ~3.9–4.3 s of scan time **and cannot overlap with itself**.

### 4.3 Waterfall #2 — Knowledge page (3 stages, 11 requests)

`frontend/app/(app)/knowledge/page.tsx:37-53`:
```
const knowledge = await getKnowledge();              // stage 1  (2 expansions)
const list      = await listProblems({...100});      // stage 2  (1 expansion)  <-- could be parallel with 1
const problems  = await Promise.all(                 // stage 3
   mostConnected.slice(0,8).map(i => getProblem(i.slug)));
```
Stage 2 is unconditionally sequenced after stage 1 even though the two requests are independent.

### 4.4 Waterfall #3 + HTTP N+1 — Problems page (~55 requests)

`frontend/app/(app)/problems/page.tsx:66-76`:
```
const [filtered, unfiltered] = await Promise.all([ listProblems(filtered), listProblems(all) ]);  // 2 reqs
const all = await Promise.all(unfiltered.items.map(item => getProblem(item.slug)));               // ~52 reqs
const drawerProblem = slug ? await getProblem(slug) : null;                                       // 1 req
```
Three sequential stages, and stage 2 is a **fan-out of one HTTP request per problem** because "the table renders attempts, languages and best runtime - all derived from the full problem" (comment at `problems/page.tsx:69-73`). The `getProblem` loop waits for **both** list calls first. The effect dependency array is
`[raw.q, raw.difficulty, raw.status, raw.sort, slug]` (`problems/page.tsx:81`) — so **every keystroke/filter change re-runs the entire 55-request sequence**, and filter updates are pushed to the URL immediately (`problems-browser.tsx:119,181`, no debounce).

### 4.5 HTTP N+1 — Submissions page (~55 requests, two variants)

`frontend/app/(app)/submissions/page.tsx:53-73`:
- list mode: `Promise.all([listSubmissions(...), listProblems(...).then(list => Promise.all(list.items.map(getProblem)))])` -> 1 + 1 + ~52 requests.
- detail mode (`?id=`): `getSubmission` -> `listProblems` -> ~52 `getProblem` — **fully sequential, 3 stages**, just to find the one problem a submission belongs to.

Effect deps `[raw.id, raw.q, raw.status, raw.language]` (`submissions/page.tsx:88`) re-fire the whole fan-out on every filter/typing change.

### 4.6 Duplicate requests

- **Per page:** `GET /health` from the sidebar's `MemoryStatus` (`components/app/sidebar.tsx:190-214`) and `GET /settings` from the root `SettingsProvider` (`components/app/settings/settings-provider.tsx:148`) fire on **every** route. Both are needed only marginally.
- **Dev mode doubles everything:** `next.config.ts` does not set `reactStrictMode`, so Next's default (React StrictMode on) is in force. StrictMode mounts/unmounts effects twice in development, so each `useEffect(fetch)` runs twice. On the Problems page that is ~104 `getProblem` requests instead of ~52. **INFERRED** (config + React semantics; not observed live).
- **`getAnalytics` and `getDashboard` are each called once per mount** — no route-loader duplication; that part is clean.

### 4.7 Unnecessary initial requests (classification)

| Request | Page | Class |
|---|---|---|
| `GET /health` (sidebar) | all app pages | **DEFERRED** — cosmetic "Index: N problems" widget |
| `GET /settings` (provider) | all app pages | **IMPORTANT** (theme/appearance), not needed for first content |
| `GET /learning/profile`, `/insights`, `/learning/recommendations`, `/learning/roadmap` | Analytics | **DEFERRED** — analytically heavy; below the fold |
| `GET /problems?page=1&page_size=100` (second, unfiltered) | Problems | **IMPORTANT** (filter-chip counts) |
| `GET /problems/{slug}` x ~52 | Problems, Submissions, Knowledge | **UNNECESSARY as designed** — replaceable by one richer list payload |
| `GET /learning/roadmap` | Analytics | **DEFERRED** |
| `POST /leetcode/auth/validate` (network) | Settings | **DEFERRED** (network hit) |

### 4.8 Expensive client components

- `knowledge-graph.tsx` (21.4 KB) renders an SVG graph; `personalized-roadmap-card.tsx` (14.3 KB) and `collective-insights-card.tsx` (14.0 KB) render long structured lists. All are below the fold on Analytics and could be code-split (`next/dynamic`); none currently is.
- `app/page.tsx` (the marketing landing) is statically rendered from `lib/mock/*` (including `mock/problems.ts`, 22.9 KB) — this is dead weight in the shared bundle for the app routes, and it also means `/` shows example data (`lib/data.ts` reads mocks; the dashboard even imports `getEvolutionStory` from `lib/mock/snippets`).
- Not one component uses `React.memo`/virtualisation, but the largest lists here are ~50–90 rows, so list rendering is **not** a material cost today. **SUSPECTED LOW**

### 4.9 `Reveal` adds a 380 ms opacity transition after data has loaded

`components/system/reveal.tsx` sets `opacity: 0` until an IntersectionObserver callback fires; `globals.css` transitions over `--duration-meaningful: 380ms`. Every `Reveal`-wrapped section therefore fades in over ~380 ms *after* its data has already arrived, which compounds the perceived delay on the analytics/dashboard cards. **MEASURED (CSS) / INFERRED (perception)**

### 4.10 No caching, no retry, no abort

`lib/api/client.ts` sets `cache: "no-store"` and has no request cache, no dedupe, no retry, and no `AbortController`. `lib/api/async-state.ts` exists (a `loading/success/error` union + `toAsyncState`) but **is not used by any page** — pages hand-roll the same union. A failed first fetch (e.g. the frontend loading before the sidecar is healthy) leaves the page in an error state with no automatic retry.

### 4.11 Client render cost

Router-level and list-level renders are cheap; the notable render work is `mappers.ts` (31 mapping functions, 16.9 KB) walking every response object, and the Analytics cards each re-mapping their payload. **INFERRED LOW**
---

## 5. API Findings

### 5.1 Every route does synchronous work on a shared service

`src/api/app.py::lifespan` builds **one** `CodeMemoryService` and stores it on `app.state`; `dependencies.get_service` returns it. That part is correct — no per-request service construction. But **every handler is `def`, not `async def`**, so each request occupies an anyio threadpool worker for its full duration. Because the work is CPU-bound Python plus a single shared DuckDB connection, extra workers do not buy throughput (see 5.3).

### 5.2 Full-dataset expansions per endpoint (code-verified call counts)

`storage.list_all()` (labelled "expansion") costs **~200 ms warm**. Counts below are read from the call sites:

| Endpoint | Handler | Expansions | Other storage work | INFERRED latency (warm) |
|---|---|---:|---|---:|
| `GET /health` | `routes/health.py:15` -> `service.health_check()` | 2–3 | `tier_health`, memory index (first call), search | ~0.4–0.6 s |
| `GET /dashboard` | `routes/dashboard.py` | **7** | + revision queue = +35 expansions | ~8.7 s |
| `GET /analytics` | `routes/analytics.py` | **5** | 1 SQL aggregate (languages) | ~1.0 s |
| `GET /problems` | `routes/problems.py:27` | 1 | Python filter/sort/paginate + full `model_dump()` | ~0.2 s |
| `GET /problems/{slug}` | `routes/problems.py:64` | 1 single-problem | — | ~2 ms |
| `GET /problems/{slug}/evolution` | `service.get_solution_evolution` | 1 single-problem | evolution service | ~2 ms + |
| `GET /submissions` | `routes/submissions.py:21` | 1, **+1 more if `problem=` filter** (`submissions.py:52`) | flatten + sort | ~0.2–0.4 s |
| `GET /submissions/{id}` | `service.get_submission` | 0 (PK lookup via `get_submission_by_external_id`) | — | fast |
| `GET /analytics/knowledge` | `GET /knowledge` | 2 (`get_knowledge_graph` + `get_knowledge_clusters`) | graph build | ~0.4 s |
| `GET /revision` | `routes/revision.py:20` | **1 + N** (see 5.3) | — | ~7.3 s |
| `GET /search` | `routes/search.py:24` -> `service.global_search` | **2** (calls `list_problems()` twice: `service.py:688,719`) | ILIKE-free Python scan of all submission code | ~0.4 s |
| `GET /insights` | `routes/insights.py` -> `service.get_grounded_insight` | **7** + ≤10 single-problem lookups | `_add_cached_submission_snapshots` calls `storage.get_by_id` per struggle (`evidence_builder.py:419,433`) | ~1.5–1.7 s |
| `GET /insights/topic/{topic}` | | 7 | same shape | ~1.5 s |
| `GET /insights/problem/{slug}` | | 1 single-problem + cached analyses | — | fast |
| `GET /learning/profile` | `service.get_collective_learning_insight` | **~10** (evidence 7 + `_get_all_problems` + recommendations 2) | + `build_collective_learning_insight`, cached analyses | ~2.0 s |
| `GET /learning/recommendations` | `service.get_next_problem_recommendations` | 2 | `build_learning_profile` + `problem_source.list_candidates()` | ~0.4 s |
| `GET /learning/roadmap` | `service.get_personalized_roadmap` | 2 | `build_learning_profile` + candidates + roadmap build | ~0.4 s |
| `GET /learning/submissions/{id}` | `service.get_submission_learning_analysis` | 1 | linear scan over all problems/attempts/submissions to find the ID | ~0.2 s |
| `GET /learning/patterns` | `service.get_submission_pattern_insights` | 7 (same evidence builder) | — | ~1.5 s |
| `GET /problems/{slug}/optimization` | | 1 single-problem + `build_problem_evidence` | — | fast |
| `GET /settings` | `routes/settings.py` | 0 | JSON file reads (`settings.json`, account JSON) | fast |

`GET /learning/profile` is the clearest case of duplicated work inside one request: `service.py:1075-1090` builds the full evidence bundle (7 expansions), **then** calls `analytics_service._get_all_problems()` again (line 1081), **then** `get_next_problem_recommendations` -> `build_learning_profile` -> `analytics._get_all_problems()` again (`learning/profile.py:85`), **then** `_recommendation_pool` -> `problem_source.list_candidates()` -> `storage.list_all()` again (`learning/sources.py:59`). The same whole dataset is materialised four separate ways for one response.

### 5.3 Parallel client requests are serialised server-side

`DuckDBStorage` pools one connection per db path and guards **all** access (reads included) with a per-path `threading.RLock` (`duckdb_repository.py:_lock_for`, and every method is `with self._lock`). Rationale in the docstring is correctness, and it is correct — but the consequence is that the Analytics page's 5 concurrent requests are executed **one after another** at the storage layer. Combined with the GIL for the CPU-bound Python (object construction, Polars, mapping), the wall-clock cost of the page is the **sum**, not the max, of its requests. **MEASURED (design) / INFERRED (effect)**

### 5.4 Payload shaping wastes work

- `GET /problems` builds `ProblemListItemOut(**p.model_dump())` (`routes/problems.py:59`). `p.model_dump()` **deep-serialises every attempt, submission and submission code**, then the slim list schema throws almost all of it away.
- `GET /problems/{slug}` returns `ProblemOut` including **full submission source code** for every submission on the problem. The Problems page then calls this ~52 times to get table data. Response size is bounded by the 21 KB of code in this DB, i.e. small today but proportional to history. **MEASURED (code size) / INFERRED (payload)**

### 5.5 Missing serialisation shortcuts

No `response_model`-level `from_attributes` construction is used; handlers hand-build Pydantic models from `model_dump()` dicts (`routes/*.py` everywhere). That is two full model traversals per response (dump then re-validate).

---

## 6. Service Findings

### 6.1 `get_revision_queue` is O(N^2) — the single worst hotspot

`src/codememory/revision/revision_service.py:119-140`:
```
problems = self.storage.list_all()          # 1 expansion
for p in problems:
    bd = self.get_problem_priority(p.id)   # per problem
```
and `get_problem_priority` (`revision_service.py:29-74`) does:
```
prob = self.storage.get_by_slug(...) or self.storage.get_by_id(...)   # single-problem expansion
weak_topics = {wt.topic for wt in self.analytics.get_topic_statistics() ...}   # FULL expansion, per problem
```
`AnalyticsService.get_topic_statistics` calls `_get_all_problems()` -> `storage.list_all()` (`analytics_service.py:180`). So the revision queue performs **1 + N full-dataset expansions**, where N is the account-scoped problem count (**35 here**).

**Computed cost:** 35 x ~207 ms + 35 x ~2 ms + 207 ms ≈ **7.5 s** for one `/revision` request (INFERRED). With a 500-problem history it would be ~104 s. Confidence HIGH on the pattern (unambiguous code), MEDIUM on the exact figure (no live server).

**Blast radius:** `/revision` (the page), **`/dashboard`** (`routes/dashboard.py` calls `get_revision_queue(limit=5)`, so the dashboard pays the full O(N^2) cost for 5 rows), and `get_due_problems` (`revision_service.py:167`, calls `get_revision_queue(limit=100)`).

### 6.2 The evidence builder re-derives the dataset 7 times per insight call

`ai/evidence_builder.py:63-114` (`build_full_profile_evidence`) calls, in order: `get_overview` (1), `get_topic_statistics` (1), `get_difficulty_statistics` (1), `get_attempt_statistics` (1), `pattern_analyzer.analyze` (1 + an inner `get_topic_statistics` = 2), `get_struggle_problems` (1) — **7 expansions**. `pattern_analyzer.analyze` also fetches its own `_get_all_problems()` (`pattern_analyzer.py:43`) *and* `get_topic_statistics`. Nothing is memoised between steps, even though every step needs the same problem graph.

### 6.3 `active_account` re-reads and re-parses a JSON file per call

`service.py:154-169` -> `leetcode` (lazy) -> `AccountService.get_connection("LeetCode")` -> `_read_all()` which does `open(file_path)` + `json.load` **every time** (`connectors/account/service.py`). Routes call `service.active_account` once each, and several service methods call it again internally when `account=None`. On the Problems page fan-out of ~52 requests that is ~52 file reads; harmless in isolation, avoidable in aggregate. **MEASURED (code)**

### 6.4 Write paths re-expand and rewrite the whole dataset

`CompositeStorage.save` does:
```
prob = self.duckdb_repo.save(problem)        # upsert
self.fs_repo.save(prob)                      # markdown write-through
self.parquet_repo.sync_all(self.duckdb_repo.list_all())   # FULL expansion + rewrite 3 parquet files
```
(`storage/composite_repository.py:38-42`). Every single problem/submission save pays one full expansion plus a full Parquet rewrite of `problems`, `attempts` and `submissions`. `RevisionService.mark_reviewed` calls `storage.save()` **twice** (`revision_service.py:181,192`), so one "mark reviewed" click = 2 expansions + 2 Parquet rewrites + 2 markdown exports. Any LeetCode sync that persists submissions one at a time becomes O(K x N). **MEASURED (code)**

### 6.5 Global search scans twice and scans code linearly

`service.global_search` (`service.py:663-780`) calls `self.list_problems()` once for problems and **again** for submissions (`service.py:688,719`) — 2 expansions — and the submission pass lowercases and substring-searches every submission's code in Python. **MEASURED (code)**

### 6.6 No caching layer anywhere on the read path

There is no memoisation of `list_all()`, no analytics result cache, no HTTP cache headers, no ETag, and no client-side request cache. The only cache in the system is `AICodeAnalyzer`'s in-memory/parquet cache of *past AI analyses* (`ai/analyzer.py:37-65`), and this DB contains **0** cached analyses, so it does nothing today. `InsightService` has no cache at all (`ai/insight_service.py`). **MEASURED (code)**

---

## 7. Storage Findings

**Overall classification: SLOW for the access pattern, FAST for the data volume.** The engine is fine; the access pattern is the problem.

| Layer | Finding | Label |
|---|---|---|
| DuckDB | Connection pooling is correct; one connection per path, never re-created per request. | MEASURED |
| DuckDB | **No indexes are created.** `_init_tables` defines only PK/UNIQUE (`duckdb_repository.py:241-320`); every `WHERE problem_id = ?` / `WHERE attempt_id = ?` is a full-table filter. | MEASURED |
| DuckDB | `list_all()` = 1 + 2P + A statements (299 here). | MEASURED |
| DuckDB | Every read holds a process-wide RLock, so reads cannot overlap. | MEASURED |
| DuckDB | **No read cache**: each of the ~25 expansions on the Analytics page re-queries and re-constructs the same objects. | MEASURED |
| DuckDB | `connect(read_only=True)` = 20.8 ms — connection cost is negligible. | MEASURED |
| Parquet | Write-through only; read path never touches it. `sync_all` rewrites 3 files on every save. | MEASURED |
| Markdown | Write-through export only. `FilesystemStorage.health()` is just `root_dir.is_dir()` (`fs_repository.py:196-198`) — **no directory traversal at request time.** The 150-dir/579-file knowledge tree is not walked on load. | MEASURED |
| Markdown | `FilesystemStorage.list_all()` would walk and parse all 579 files, but nothing on the API read path calls it (reads stop at DuckDB). | MEASURED |

Ruled out as a cause: Markdown traversal and Parquet reads are **not** on the UI critical path.

---

## 8. AI Findings

1. **Is AI called during initial UI load?** Only on Analytics, via `GroundedInsightCard` -> `GET /insights` (`components/app/grounded-insight-card.tsx:38`).
2. **Which pages trigger AI?** Analytics (`/insights`), the problem drawer (`/problems/{slug}/optimization`, `/learning-analysis`), and the submission learning card (`/learning/submissions/{id}`).
3. **Are AI calls blocking?** They block their own request, and because of the shared storage lock they also queue behind storage work; but the provider call itself is what the card waits on.
4. **Is the provider on the critical path today?** **No.** No `.env` exists; `AI_PROVIDER` is unset and `OPENAI_API_KEY` is unset (`Get-ChildItem -Force -Filter ".env*"` -> only `.env.example`; env vars empty), so `get_ai_provider()` returns `HeuristicAIProvider()` (`ai/providers/__init__.py:14-31`). Heuristic interpretation is deterministic and sub-millisecond.
5. **Model initialisation is lazy.** `Qwen3Provider.__init__` only resolves a model name/base URL (default `http://localhost:11434/v1`); the client is created inside `_call_model` per call (`ai/providers/qwen_provider.py:67-144`). No model is preloaded at process start.
6. **Is Qwen already running?** No Ollama/llama process was found (`Get-Process` filtered); nothing listens on 11434. Not verified per-port; treated as UNKNOWN.
7. **Prompt/evidence size:** the evidence bundle for a full profile contains every topic row, difficulty row, pattern item and up to 10 supporting problems (`ai/evidence_builder.py`, serialised by `serialize_evidence` in `ai/providers/base_provider.py`). It is built from scratch on **every** call (no cache), so the expensive part is evidence construction, not prompt size.
8. **Deterministic work is repeated before every AI call** — that is 8.1 point 4 above: ~7 expansions of deterministic work precede a heuristic interpretation that needs none of it.
9. **Duplicate AI calls:** the Analytics page calls `/insights` once; no duplication observed.
10. **Risk:** if `AI_PROVIDER=qwen` is set and the local runtime is cold, every insight request will block on a model load/HTTP round trip **in addition to** the ~1.5 s of evidence construction, with no cache and no streaming. **SUSPECTED**

**AI is therefore not a blocking factor today, but the insight endpoints are already the second-most-expensive ones for reasons unrelated to AI.**

---

## 9. Network / LeetCode Findings

- **No network activity on app start.** `CodeMemoryService.__init__` builds `problem_source` via `build_problem_source(...)`, which with the default `CODEMEMORY_PROBLEM_SOURCE=local` returns `LocalCatalogSource` (no client, no I/O beyond `storage.list_all()`); the remote source is only constructed when the env enables it (`learning/sources.py:100-130,272+`). `.env.example` documents the default as `local`.
- **Autosync does not start on its own.** `_autosync` is `None` until `service.autosync` is touched (`service.py:156-160,1297+`), and `routes/settings.py:14-16` deliberately reads `service._autosync` (underscore) so merely loading Settings cannot spawn the worker. No scheduler thread is started at startup. **MEASURED (code)**
- **One real network call exists in the UI:** the Settings page's account section runs `Promise.allSettled([getLeetCodeStatus(), validateLeetCodeCredentials()])` (`components/app/settings/account-section.tsx:72`). `validate_authenticated_credentials()` makes "one authenticated read-only request" to LeetCode (`connectors/leetcode/service.py:316-332`). `getLeetCodeStatus()`/`status()` is local file reads only (`service.py:258+`). So a LeetCode round trip can block the Settings page's account panel. **MEASURED (code)**
- **The Tauri readiness probe is a network call:** `reqwest::blocking::get("http://127.0.0.1:8000/api/v1/health")` every 500 ms, up to 30 s (`src-tauri/src/sidecar.rs:8,110-150`). That is loopback, but each successful probe invokes the *expensive* `/health` handler.
- **Bundle/asset delivery is local** (Tauri asset protocol serving `frontend/out`), so there is no CDN/DNS latency for the UI itself.

---

## 10. Background Work

- **Autosync / scheduler:** not started by the API process unless the settings UI enables it (`_autosync` stays `None`). When enabled it is a daemon thread (`connectors/leetcode/scheduler.py:260-262`) that would write through `CompositeStorage.save` — i.e. full-dataset expansion + Parquet rewrite per saved problem — **while the UI is reading the same locked DuckDB connection**. That is a genuine contention path. **INFERRED (not active in the observed state)**
- **No polling, watchers, health checks or analytics refresh run in the background.** The only recurring loop is the Tauri startup health poll, which stops once healthy. **MEASURED (code)**
- **Startup jobs:** the FastAPI lifespan only constructs the service. `AICodeAnalyzer._load_cache` reads `data/ai_analyses.parquet` (21.7 KB) at construction; `MemoryEngineService`/`SemanticIndex` initialise lazily. No index rebuild at startup. **MEASURED (code)**
- **CPU contention today is self-inflicted, not background:** the API threadpool working on ~25 serialised expansions for one page is the contention.
- **Resource snapshot.** No Python/Node/Next/Ollama process was running (`Get-Process` found no `python`, `node` app server, `qwen`, `ollama` — only harness Node processes <9 MB). CPU/RAM/disk during a load were therefore **UNKNOWN**.
---

## 11. Page-by-Page Performance (INFERRED unless noted)

All pages also pay `GET /health` (sidebar) and `GET /settings` (root provider).

| Page | Initial Load | API Calls | Slowest Request | Main Bottleneck |
|---|---:|---:|---|---|
| Dashboard | skeleton until `/dashboard` resolves | 3 (+0 fan-out) | `GET /dashboard` (~8.7 s est.) | revision queue O(N^2) + 7 expansions |
| Analytics | skeleton until `/analytics`; then 4 cards appear progressively | 7 | `GET /learning/profile` (~2.0 s est.) | 5 serialised requests doing ~25 expansions total |
| Problems | skeleton, then one fan-out | ~57 | `GET /problems` list (~0.2 s each) + 52 detail calls | HTTP N+1 fan-out; re-fires on every filter change |
| Submissions | skeleton, then one fan-out | ~56 | `listSubmissions` + `listProblems` (~0.2 s each) | HTTP N+1 fan-out; detail mode is 3 sequential stages |
| Knowledge | 3 sequential stages | ~12 | `GET /knowledge` (~0.4 s) | avoidable sequential `getKnowledge` -> `listProblems` |
| Revision | skeleton until `/revision` resolves | 3 | `GET /revision` (~7.3 s est.) | revision queue O(N^2) |
| Settings | provider settings from cache; account panel pending | ~4 | `POST /leetcode/auth/validate` (network) | external LeetCode round trip |
| Search | idle until typed | 3+ | `GET /search` (~0.4 s per query) | 2 expansions + linear code scan per debounce |
| `/` (landing) | static, mock data | 0 | — | none (not an API page) |

Not measurable: browser paint timings, React commit counts, hydration time, and any per-request end-to-end latency (no server running).

---

## 12. Critical Path

**Analytics page (the clearest "small but noticeable delay" case), warm process:**

```
Static HTML/JS parse + hydrate shell ...................... UNKNOWN (not profiled)
SettingsProvider -> GET /settings ......................... ~fast (file reads)
Sidebar -> GET /health .................................... ~0.4 s   (2-3 expansions)   [INFERRED]
AnalyticsPage effect -> GET /analytics .................... ~1.0 s   (5 expansions)      [INFERRED]
  -> React renders charts (state === success)
  4 cards mount in parallel, but serialise on the DuckDB lock:
     GET /learning/profile ............................... ~2.0 s   (~10 expansions)   [INFERRED]
     GET /insights ........................................ ~1.5 s   (7 expansions)      [INFERRED]
     GET /learning/recommendations ........................ ~0.4 s                        [INFERRED]
     GET /learning/roadmap ................................ ~0.4 s                        [INFERRED]
  4 x Reveal fade-in ..................................... +380 ms each (overlapped)
-------------------------------------------------------------
CRITICAL PATH (storage work, warm) ....................... ~5.3 s   [INFERRED]
```

**Dashboard page, warm process:**

```
GET /settings + GET /health ............................... ~0.4 s
GET /dashboard ............................................ ~8.7 s
   = 7 expansions                     ~1.4 s
   + get_revision_queue(limit=5)      ~7.3 s  <-- dominant term
-------------------------------------------------------------
CRITICAL PATH ............................................. ~9.1 s   [INFERRED]
```

**Cold process (no server running yet):** add ~1.0 s of Python import (`api.app`), plus DuckDB open and first-expansion cold penalty (693 ms vs 200 ms), plus — in a packaged build — PyInstaller onefile extraction and the Tauri health loop (UNKNOWN).

These are the numbers to replace with live measurements (`curl -w`/mid-logger per endpoint) before optimising. What is *not* in doubt is the shape: the time is spent in repeated storage expansion, on the server, before the client can render.

---

## 13. Ranked Blocking Factors

### P0 — Critical

**P0-1. `get_revision_queue` re-expands the whole dataset once per problem (O(N^2))**
- Location: `src/codememory/revision/revision_service.py:119-140` (loop) and `:29-74` (`get_problem_priority` -> `analytics.get_topic_statistics()`).
- Evidence: code; measured expansion cost (~207 ms warm, 693 ms cold); N = 35 scoped problems.
- Measured impact: ~7.3 s computed for `/revision`; the same cost is paid by `/dashboard` (`routes/dashboard.py`) and `get_due_problems`.
- Affected pages: Dashboard, Revision.
- Blocks initial render: yes (both pages show only a skeleton until the response).
- Cold/warm: both (cold worse by the first-expansion penalty).
- Confidence: **HIGH** on the pattern, **MEDIUM** on the exact magnitude.

**P0-2. `storage.list_all()` is an N+1 query expansion with no cache**
- Location: `src/codememory/storage/duckdb_repository.py:474-572`.
- Evidence: 299 statements measured at 190–217 ms warm / 693 ms cold (with model construction); 299 trivial statements = 36.8 ms; no indexes; every read under the shared lock.
- Measured impact: sets the floor for *every* analytics/insight/learning endpoint.
- Affected pages: all data pages.
- Blocks initial render: yes.
- Confidence: **HIGH**.

**P0-3. One request repeats the same expansion many times**
- Location: `ai/evidence_builder.py:63-114` (7 expansions), `service.py:1075-1160` (`/learning/profile` ≈ 10), `analytics_service.py:101-467` (each `get_*` re-fetches), `pattern_analyzer.py:43`.
- Evidence: call counts in code; measured per-expansion cost.
- Measured impact: `/analytics` ≈ 1.0 s of redundant re-reads; `/learning/profile` ≈ 2.0 s; `/insights` ≈ 1.5 s.
- Affected pages: Analytics (5 requests totalling ~25 expansions), Dashboard.
- Blocks initial render: yes on Analytics (stage 1 gates everything).
- Confidence: **HIGH**.

**P0-4. Frontend HTTP N+1 fan-out on Problems / Submissions / Knowledge**
- Location: `problems/page.tsx:66-76`, `submissions/page.tsx:53-73`, `knowledge/page.tsx:37-50`.
- Evidence: ~52 `GET /problems/{slug}` per page mount; effect deps re-run on every filter keystroke (`problems/page.tsx:81`, `submissions/page.tsx:88`); filter updates are pushed to the URL with no debounce (`problems-browser.tsx:119,181`).
- Measured impact: ~55 requests per mount; ~104 in dev with StrictMode double-invocation. Each request returns full submission code.
- Affected pages: Problems, Submissions, Knowledge.
- Blocks initial render: yes (table renders only after all detail calls resolve).
- Confidence: **HIGH** (code) / MEDIUM on live latency.

### P1 — High

**P1-5. Parallel client requests are serialised by one DuckDB lock + the GIL**
- Location: `duckdb_repository.py:_lock_for` + `with self._lock` on every read.
- Evidence: design; analytics page fires 5 concurrent requests; Python is CPU-bound.
- Impact: page cost = sum of requests, not max. Parallelism buys nothing today.
- Confidence: **HIGH** (design), **MEDIUM** (measured effect, needs live confirmation).

**P1-6. `GET /health` is heavy and is called by the shell on every page (and polled at startup)**
- Location: `components/app/sidebar.tsx:190-214`; `service.py:1190-1240` (`len(storage.list_all())`); `search_service.py:32` (another expansion); `memory/service.py:130-148` (expansion on first call); `routes/health.py`.
- Evidence: 2–3 expansions per call; the Tauri probe polls it every 500 ms.
- Impact: ~0.4–0.6 s added to **every** page load for a cosmetic widget; delays sidecar readiness.
- Confidence: **HIGH**.

**P1-7. Tauri blocks `setup` on a synchronous sidecar health loop; the sidecar is PyInstaller onefile**
- Location: `src-tauri/src/lib.rs:17` (`sidecar::start(app.handle())` in `setup`), `src-tauri/src/sidecar.rs:8-150`; `backend/codememory-api.spec` (onefile `EXE(...a.binaries, a.zipfiles, a.datas...)`, `console=True`).
- Evidence: code; `dist/` is empty so the exe could not be timed; `import api.app` = 987 ms is a lower bound on process warm-up.
- Impact: the window is not usable until the backend is healthy; onefile extracts to a temp dir on every launch.
- Cold/warm: cold-start only.
- Confidence: **HIGH** (code), **UNKNOWN** (magnitude).

**P1-8. Backend cold-start import cost ~1 s**
- Evidence: `import api.app` = 987 ms; `codememory.core.service` = 836 ms; domain models = 275 ms. **MEASURED**
- Impact: adds to first-response latency after every sidecar launch (dev and packaged).
- Confidence: **HIGH**.

### P2 — Medium

**P2-9. React StrictMode doubles every initial fetch in dev** — `next.config.ts` omits `reactStrictMode` (default true); every page fetch is in `useEffect`. Turns ~55 requests into ~104 on the Problems page in `tauri dev`. Confidence: **MEDIUM** (not observed live).

**P2-10. `Reveal` delays content that has already loaded** — `components/system/reveal.tsx` (opacity 0 until IO fires) + `--duration-meaningful: 380ms` in `globals.css`. Confidence: **HIGH** (CSS/code), LOW on perceptual weight.

**P2-11. Turbopack dev on-demand compilation** — `tauri.conf.json` `beforeDevCommand: "npm run dev"` + `devUrl: http://localhost:3000`. In dev, each route is compiled on first visit, adding seconds unrelated to the backend. Confidence: **MEDIUM** (UNKNOWN magnitude).

**P2-12. List endpoints deep-serialise then discard** — `routes/problems.py:59` (`ProblemListItemOut(**p.model_dump())`) serialises all attempts/submissions/code, then drops them. Confidence: **HIGH** (code), LOW impact at current size.

**P2-13. Every write re-expands the dataset and rewrites all Parquet tiers** — `composite_repository.py:38-42`; `mark_reviewed` saves twice (`revision_service.py:181,192`). Confidence: **HIGH** (code).

**P2-14. `active_account` re-reads/re-parses JSON per call** — `connectors/account/service.py::_read_all`. Confidence: **HIGH** (code), LOW impact alone.

### P3 — Low

**P3-15. `global_search` expands twice per query** — `service.py:688,719`. Confidence: **HIGH**.
**P3-16. No read caching exists anywhere** — `list_all`, analytics, evidence and insights are recomputed per request. Confidence: **HIGH**.
**P3-17. Legacy Streamlit launcher and old DB backup in `data/`** (`run.ps1`, `data/codememory.duckdb.pre-ownership-v1.bak`, 6 MB) are dead weight but not read at runtime. Confidence: **HIGH** (no impact).
**P3-18. Landing page ships mock data in the shared bundle** (`lib/mock/*` incl. 22.9 KB `problems.ts`; `lib/data.ts` reads mocks). Confidence: **MEDIUM**.
---

## 14. Root Causes vs Symptoms

| Reported / observed | What it actually is | Root cause |
|---|---|---|
| "Analytics page takes a couple of seconds" | Symptom | 5 endpoints each independently re-derive the whole history (25 expansions), serialised on one DuckDB lock (P0-3 + P1-5) |
| "Dashboard feels slow to become usable" | Symptom | `get_revision_queue` is O(N^2) because `get_problem_priority` re-runs `get_topic_statistics()` per problem (P0-1) |
| "Problems/Submissions pages stall, and typing in the filter is laggy" | Symptom | One HTTP request per problem (~52) in a 3-stage waterfall, re-fired on every filter change (P0-4) |
| "Everything is a bit slow, even when warm" | Symptom | No read cache + N+1 `list_all` (299 statements) sets a ~200 ms floor per expansion (P0-2, P3-16) |
| "First launch after opening the app is slower" | Symptom | PyInstaller onefile extract + Tauri blocking health loop + ~1 s Python import (P1-7, P1-8) |
| "Cards pop in one after another" | Symptom | Stage-gated rendering in `analytics/page.tsx` + `Reveal`'s 380 ms fade (P0-3, P2-10) |
| "The sidebar says 'Checking' then shows the index" | Symptom | Shell-side `/health` call that itself expands the dataset 2–3 times (P1-6) |

**The single deepest root cause** is that CodeMemory has no materialised view of the user's history: every analytics/insight/learning feature re-derives it from DuckDB in Python, one problem at a time, and one of those features (revision scoring) re-derives it *inside a loop over the problems*. Everything else (waterfalls, fan-out, reveal, strict mode) is additive noise on top.

---

## 15. Quick Wins (candidates only — NOT implemented)

Ordered by value/risk. Each is a *proposal*, not a change.

1. **Hoist `get_topic_statistics()` out of the `get_problem_priority` loop.** Compute `weak_topics` once in `get_revision_queue` and pass it in. Removes ~35 expansions from `/revision` and `/dashboard`. (P0-1)
2. **Memoise `list_all()` per request** (or per service generation) so `/analytics`, `/dashboard`, `/insights`, `/learning/profile` reuse one expansion instead of 5–10. (P0-2/P0-3)
3. **Batch the problem-detail fetch**: make `GET /problems?page_size=100` return the table fields the Problems page needs (attempt counts, languages, best runtime) so the ~52 `getProblem` calls disappear. (P0-4)
4. **Make `/health` cheap**: return a cached/constant status, or drop `len(storage.list_all())` and the search probe, so the sidebar and the Tauri probe stop paying for a full expansion. (P1-6)
5. **Add one index** on `attempts(problem_id)` and `submissions(attempt_id)`, or replace `list_all`'s per-row queries with three bulk queries joined in Python (1 + 3 statements instead of 1 + 2P + A). (P0-2)
6. **Debounce the Problems/Submissions filter -> URL push** and stop refetching the unfiltered set on every keystroke. (P0-4)
7. **Defer the Analytics insight cards** until after the page is interactive, or fire them in parallel with `/analytics` instead of after it. (P0-3)
8. **Cache insight/evidence bundles** with a short TTL (they are pure functions of stored data). (P3-16)
9. **Drop the `Reveal` opacity gate** for above-the-fold data sections, or reduce the duration. (P2-10)
10. **Parallelise `getKnowledge()` and `listProblems()`** on the Knowledge page. (P0-4)

---

## 16. Architectural Improvements (NOT implemented)

1. **Introduce a single "history snapshot" read model.** Load the problem/attempt/submission graph once per request (or once per short TTL) and pass it to `AnalyticsService`, `PatternAnalyzer`, `RevisionService`, `EvidenceBuilder` and the learning layer, instead of each service fetching it. This removes the entire class of P0-2/P0-3 findings.
2. **Move analytics to SQL.** `get_overview`, `get_topic_statistics`, `get_difficulty_statistics`, `get_progress_over_time` and the revision score are all aggregations; DuckDB can compute them in one query each (as `get_language_statistics`, `get_streaks` and `get_activity_heatmap` already do) instead of materialising 52 Pydantic object graphs.
3. **Separate the write model from the export model.** `CompositeStorage.save` currently expands the whole dataset and rewrites all Parquet tiers per write; incremental/append-only export would decouple write cost from history size.
4. **Cache at the API boundary with explicit invalidation on write** (`/analytics`, `/dashboard`, `/learning/*`, `/insights`), keyed by account + data version.
5. **Precompute the revision queue** (it is the same computation for `/dashboard`, `/revision` and `get_due_problems`) rather than recomputing per caller.
6. **Make the transport a single aggregate per page** (a BFF-style `/dashboard/overview`, `/analytics/full`) so the client stops fanning out and stops depending on request ordering.
7. **Ship the sidecar as one-folder** instead of onefile, and/or start the sidecar before the window is shown without blocking `setup`.
8. **Read path indexes / column pruning** in DuckDB so child-row loads are index lookups rather than table filters.

---

## 17. Recommended Optimization Order

Based on measured evidence (biggest measured coefficient first, cheapest change first):

1. **Remove the per-problem `get_topic_statistics()` call in the revision scorer** (P0-1). Highest measured impact per line changed; unblocks Dashboard *and* Revision.
2. **Deduplicate the expansions inside each request** (`/learning/profile` materials the dataset 4x; the evidence builder 7x) (P0-3).
3. **Make `list_all()` one expansion per request and cache it for the request's lifetime** (P0-2).
4. **Replace the Problems/Submissions detail fan-out with fields in the list payload** (P0-4).
5. **Make `/health` constant-time** so every page stops paying for it (P1-6).
6. **Add indexes / bulk child queries** to cut the ~200 ms per-expansion cost at the source (P0-2).
7. **Debounce filter-driven refetches and drop the Reveal gate** (P0-4, P2-10).
8. **Then** address startup: sidecar packaging + Tauri readiness (P1-7, P1-8).
9. **Then** consider an API-level cache (P3-16) — it is a multiplier on whatever the above leaves.

Rationale: 1–3 are surgical, all measured to be on the critical path, and each removes whole seconds rather than milliseconds. 4 removes an entire class of network waterfalls. 5–7 remove per-page fixed costs. 8–9 matter for the perceived "app open" moment and for growth.
---

## 18. Measurement Gaps

| Gap | Why | How to close it |
|---|---|---|
| No endpoint was timed end to end | No server was running (`GET /health` refused; nothing listening on 8000/3000) and starting one would have written to the DuckDB file, which the audit forbids | Run the API and time each route with `curl -w "%{time_total}"` or add a timing middleware in a separate task |
| Byte sizes of API responses | Same reason | `curl -s -o NUL -w "%{size_download}"` per endpoint |
| `CodeMemoryService` construction cost | `__init__` performs DDL + hash repair (writes) | Measure in a throwaway `:memory:` or copied DB |
| PyInstaller onefile extraction cost | `dist/` is empty; no built sidecar | Time a packaged launch |
| Tauri window-show timing and Rust build | `src-tauri/target` is absent; no release build | Build and instrument with `tauri-plugin-log` timings |
| Browser paint/hydration/React commit timings | No browser automation or DevTools profiling available in this environment | Chrome DevTools Performance / Lighthouse on the exported `out/` |
| Whether StrictMode actually doubles requests at runtime | Inferred from config defaults | Watch the API access log during `next dev` |
| CPU/RAM/disk during a load | No app processes were running | Sample `Get-Counter`/Task Manager during a real load |
| Qwen/OpenAI latency | Not configured (`AI_PROVIDER` unset, no key, no Ollama process) | Only measure if the user intends to run a local/remote model |
| `list_all()` cost on a *larger* history | This DB is only 52 problems | Re-measure with a synthetic 500/2000-problem fixture |

Every "~X s" per-endpoint figure in this document is an **estimate built from measured primitives and verified call counts**, not a live observation. The *shape* of each finding (which code runs, how many times, under which lock) is code-verified and does not depend on the estimate.

---

## 19. Confidence

| Conclusion | Confidence |
|---|---|
| `list_all()` is an N+1 expansion costing ~200 ms warm / ~690 ms cold, uncached | **HIGH** (measured) |
| `get_revision_queue` is O(N^2) via `get_problem_priority` -> `get_topic_statistics` per problem | **HIGH** on pattern, **MEDIUM** on magnitude |
| `/dashboard` and `/revision` are the slowest endpoints | **MEDIUM** (computed; single dominant term identified in code) |
| Analytics page issues 5 requests / ~25 expansions, serialised | **HIGH** on counts, **MEDIUM** on totals |
| Problems/Submissions pages fan out ~52 HTTP requests and re-fire per keystroke | **HIGH** (code), **MEDIUM** (live latency) |
| Server-side parallelism is neutralised by one DuckDB lock + GIL | **HIGH** (design), **MEDIUM** (measured effect) |
| `/health` is called per page and expands the dataset 2–3 times | **HIGH** |
| Backend cold-start import ~1 s | **HIGH** (measured) |
| Tauri blocks on the sidecar health loop; onefile extraction adds cold-start cost | **HIGH** on the loop, **UNKNOWN** on extraction magnitude |
| AI is not on the critical path today | **HIGH** (env inspected) |
| Markdown/Parquet are not on the read path | **HIGH** |
| Frontend bundle is not the bottleneck | **MEDIUM** (~657 KB route JS + static local delivery; no profiling) |
| `Reveal`'s 380 ms fade contributes perceptibly | **MEDIUM** |
| StrictMode doubles dev requests | **MEDIUM** |

---

# Final Deliverable

### A. Top 5 blocking factors

1. **Revision-queue O(N^2)** — `revision_service.py:119-140` loop calling `get_problem_priority` (`:74` re-runs `analytics.get_topic_statistics()` per problem). Hit by `/revision` **and** `/dashboard`. ~7.3 s computed.
2. **N+1 `list_all()` with no cache** — `duckdb_repository.py:474-572`; 299 statements, ~200 ms warm / ~690 ms cold; sets the floor for every analytics endpoint.
3. **Per-request repeated full-history derivation** — evidence builder 7x (`evidence_builder.py:63-114`), `/learning/profile` ~10x (`service.py:1075-1160`).
4. **HTTP N+1 fan-out on Problems/Submissions/Knowledge** — ~52 `GET /problems/{slug}` per mount, re-fired per filter change (`problems/page.tsx:66-81`, `submissions/page.tsx:53-88`, `knowledge/page.tsx:37-50`).
5. **`GET /health` on every page + at startup, itself 2–3 expansions** — `sidebar.tsx:190-214`, `service.py:1190-1240`, polled by the Tauri probe.

### B. Top 5 highest-value optimizations

1. Hoist `get_topic_statistics()` out of the revision-scoring loop (compute once per request).
2. Single memoised history snapshot per request, shared by analytics/patterns/revision/evidence.
3. Bulk child queries (or index `attempts.problem_id` / `submissions.attempt_id`) to collapse 299 statements to ~4.
4. Return table fields from `GET /problems` so the ~52 detail requests disappear.
5. Make `/health` constant-time.

### C. Expected affected layer

| # | Layer |
|---|---|
| 1 | Backend service (`RevisionService` + `AnalyticsService`) |
| 2 | Storage (`DuckDBStorage`) + service cache |
| 3 | Backend service (analytics/evidence/learning orchestration) |
| 4 | Frontend (data fetching) + API contract (`/problems` payload) |
| 5 | Backend API (`/health`) + frontend shell |

### D. Evidence supporting each

1. Loop at `revision_service.py:137-140`; `get_topic_statistics()` at `:74` -> `analytics_service.py:180` -> `_get_all_problems()`. Measured expansion 190–217 ms warm; N=35 scoped problems. Also called by `routes/dashboard.py`.
2. `list_all()` -> `_build_problem_from_row` issues attempts + per-attempt submissions + notes; measured 299 statements = 190–217 ms warm vs 36.8 ms for 299 trivial statements; no indexes in `_init_tables`; no cache.
3. `build_full_profile_evidence` calls six analytics methods (7 expansions); `get_collective_learning_insight` then calls `_get_all_problems()` again and `get_next_problem_recommendations` -> `build_learning_profile` -> `_get_all_problems()` (`learning/profile.py:85`) -> `LocalCatalogSource.list_candidates()` -> `list_all()` (`learning/sources.py:59`).
4. `problems/page.tsx:74` / `submissions/page.tsx:54,72` / `knowledge/page.tsx:50` map over the list and call `getProblem(...)`; effect deps include the search string; `problems-browser.tsx:119,181` push URL updates immediately.
5. `sidebar.tsx:190-214` mounts on every app route; `service.health_check()` counts problems via `list_all()` (`service.py:1202`), probes `search_service.search()` (another `list_all`, `search_service.py:32`) and, on first call, the memory index (`memory/service.py:130-148`); `sidecar.rs:110-150` polls it every 500 ms.

### E. Recommended implementation order

1. Revision-scoring loop fix (P0-1).
2. Per-request deduplication of expansions in analytics/evidence/learning (P0-3).
3. `list_all()` single-expansion + request-scoped cache, then indexes/bulk queries (P0-2).
4. `/problems` list payload carries table fields; drop the frontend fan-out (P0-4).
5. `/health` becomes constant-time (P1-6).
6. Debounce filter refetches; remove the `Reveal` gate (P2-9/10).
7. Startup: sidecar packaging + non-blocking Tauri readiness (P1-7, P1-8).
8. API-level cache with write invalidation (P3-16).

**No changes were made as part of this audit.** `git status --porcelain` is empty; the only file written is this report.

---

## Appendix A - Runtime verifications performed during this audit

| Check | Command (read-only) | Result |
|---|---|---|
| No indexes exist | `SELECT index_name, table_name FROM duckdb_indexes()` | `[]` (empty) - confirms every `WHERE problem_id = ?` / `WHERE attempt_id = ?` is a full-table filter |
| Tables present | `SHOW TABLES` | `account_problem_state`, `attempts`, `notes`, `problems`, `schema_migrations`, `submissions` |
| `CREATE INDEX` in repository source | `Select-String 'CREATE INDEX' duckdb_repository.py` | 0 matches |
| `account_problem_state` usage | repo-wide search | 0 references - leftover table, not a runtime cost |
| Dataset size | `count(1)` over problems/attempts/submissions/notes | 52 / 194 / 89 / 0 |
| Submission code volume | `sum(length(code))` | 21,286 chars total, 1,096 max |
| Complexity data available | `count(1) FROM attempts WHERE time_complexity IS NOT NULL` | 0 - no per-attempt complexity is stored today |
| Accounts | `GROUP BY source_account` | `shrey_sawant` 66, `JWSztSMf2l` 23 |
| No server running | `Get-NetTCPConnection -State Listen` (8000/3000/8501/1420) + `GET /api/v1/health` | nothing listening; connection refused |
| AI provider configuration | `.env*` listing, `$env:AI_PROVIDER`, `$env:OPENAI_API_KEY` | only `.env.example`; both empty -> `HeuristicAIProvider` |
| Repository untouched | `git status --porcelain` | only `?? docs/performance-audit.md` |

No file other than this report was created, modified or deleted.
