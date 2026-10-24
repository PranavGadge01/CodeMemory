# Open issues and demo risks

## Do not record a complete functional demo yet

The audited runtime did not prove a seeded end-to-end workflow. The API-backed index was empty; `/submissions` crashed; four analytics learning/insight cards returned HTTP 404. The polished homepage is explicitly illustrative and cannot stand in for those flows.

## Blockers and risks

| Priority | Issue | Evidence / recording effect | Next action |
|---|---|---|---|
| P0 | Python environment cannot run | `.venv` targets missing Windows Store Python 3.13; `py` reports no interpreter. Bundled Python 3.12 lacks dependencies. Cannot seed, test, CLI, or Streamlit. | Install Python 3.12 and create `.venv-demo`; leave `.venv` untouched. |
| P0 | API startup not independently verified | Packaged executable returned without logs; it created an isolated DB/WAL but no listener/health could be confirmed. UI read requests worked through configured API, but process/path unknown. | Start source API against a fresh isolated path; verify logs/health. Keep the generated `runtime-data` folder separate from the recording profile. |
| P0 | No indexed data | Dashboard 0 problems/submissions; problem list 0/0; graph and queue empty. | Seed synthetic records once to a new dedicated directory using explicit paths. |
| P0 | Submissions page crash | Dev log: `Cannot read properties of undefined (reading 'statusCounts')` at `frontend/components/app/submissions/submissions-browser.tsx:97`. | Resolve DTO mismatch in separate implementation work; retest. |
| P0 | Analytics learning cards 404 | Insight, next-problem, roadmap, and submission-pattern cards show HTTP 404. Source routes exist in `src/api/routes/insights.py` and `learning.py`. | Verify clean API process/version and exact mounted routes. |
| P1 | Frontend typecheck fails | Numerous TypeScript errors, including snake_case accesses against camelCase mapped types and missing `SubmissionListItem` export. | Fix contracts in separate engineering task; rerun typecheck/build. |
| P1 | Lint fails | `npm run lint`: 57 errors/10 warnings, including `no-explicit-any` in submissions and generated Tauri target JS. | Fix source findings and exclude generated outputs; rerun. |
| P1 | Next hydration diagnostics | Browser/Next output included hydration mismatches and script-in-React warning. | Verify clean production build after TS fixes and inspect target browser. |
| P1 | No import workflow in current frontend | Settings says import/rebuild/delete are unavailable; API route list has no import. CLI/Streamlit support import. | Clarify which surface is the supported buyer product and test its import workflow. |
| P1 | CLI seed defaults to repository data | `src/codememory/cli/main.py` builds default `CodeMemoryService()` before command dispatch. | Use the explicit isolated seed snippet; do not use default CLI paths. |
| P1 | Tauri/API port mismatch | Tauri CSP allows port 8000; frontend example config uses 8001. Desktop not run. | Verify sidecar/API/CSP together before recording desktop. |
| P2 | Public LeetCode sync is limited | Docs/code: recent bounded accepted submissions; no code/runtime/memory or complete history. | Use synthetic seed; report limits accurately if integration is separately tested. |
| P2 | Authenticated sync requires secrets | Session/CSRF and vault storage; not needed for this demo. | Leave disconnected and credentials untouched. |
| P2 | No roles/login | Sign-in explicitly says no account needed; no role routes found. | Describe current single-local-workspace model. |
| P2 | Other platform integrations incomplete | Codeforces and HackerRank show “Coming soon.” | Exclude from claims. |

## Fragile recording steps

- `/submissions` and related details: crash observed.
- Analytics learning/AI cards: 404 observed.
- Search/revision/graph: only empty states verified; positive behavior still needs seeded data.
- LeetCode public/authenticated sync: requires external network/account data; untested.
- Preference writes, review mutations, import/export: no writes made; test only in isolated synthetic environment.
- Streamlit/CLI default paths can overlap repository data; Python runtime unavailable.
- Landing-page metrics/evolution are illustrative, not live user records.

## Evidence boundaries

Verified: source/docs inspection; local Next dev server and browser rendering; empty API-backed states from configured local service; one empty search; LeetCode disconnected status; settings read; analytics 404s; submissions crash; typecheck and lint failures.

Not verified: clean source API startup, Python test suite, sample seed execution, positive end-to-end path, preference/review writes, import/export, AI success, account isolation, LeetCode sync, Streamlit, Tauri, or production build.

## Recommended priority order

1. Restore Python 3.12 in a new environment and run default pytest suite.
2. Start a known source API on isolated synthetic paths and verify health.
3. Seed synthetic records once; confirm nonzero dashboard and problem detail.
4. Resolve submissions DTO/runtime mismatch and analytics 404s.
5. Resolve typecheck/lint and hydration warnings; verify clean build.
6. Retest search, revision scoring, graph, settings reload, and AI cards.
7. Then record buyer-oriented sequence using synthetic data; keep LeetCode disconnected.

## Readiness follow-up — 2026-10-14

### Resolved on `codex/demo-readiness`

- Frontend DTO/domain naming mismatches in the submission pattern, problem learning, and submission learning cards were corrected to read the camelCase domain objects returned by `frontend/lib/api/mappers.ts`.
- The erroneous `SubmissionListItem` re-export from `frontend/lib/types.ts` was removed from `frontend/lib/api/resources.ts`; its public export already comes from `frontend/lib/api/mappers.ts`.
- The submissions page's `any` state was replaced with a typed state union. Frontend typecheck now passes.

### Still blocking recording

- No Python 3.12 installation; therefore no isolated venv, dependency installation, Python tests, synthetic seed, or source FastAPI runtime verification.
- No active local API or frontend listener was found. The current runtime route set and response bodies cannot be compared to the prior 404/crash report.
- The four learning/insight 404s and `/submissions` undefined filter data were not reproduced against the current source API. Treat their runtime state as unresolved.
- Full frontend lint still fails with 56 errors and 9 warnings, including generated Tauri assets and React hook effect errors. A production build was not run because the Next config exports to an existing `frontend/out/` directory; overwriting an existing output was not justified for this investigation.
- No browser workflow, persistence after restart, hydration behavior, or settings persistence was tested in this follow-up.

See `09_FINAL_READINESS_REPORT.md` for the detailed go/no-go and reproduction sequence.
