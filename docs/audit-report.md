# CodeMemory End-to-End Audit Report

## Executive Summary
The application has two parallel stacks: a Streamlit app (legacy) and a Next.js + FastAPI pair (new). The new frontend has fully wired API integration across all `/(app)/` routes, but the **landing page** still uses mock data exclusively. Critical issues found include dead code after `return`, hardcoded mock data in the sidebar MemoryStatus component, Settings error state being swallowed, and revision `mark_reviewed` not account-scoped.

---

## 1. Complete Audit Matrix

### A. Navigation Audit

| Route | Status | Notes |
|-------|--------|-------|
| `/` (landing) | Works | Uses mock data |
| `/dashboard` | Works | Fully API-driven |
| `/problems` | Works | Deep-link via `?slug=` opens drawer |
| `/submissions` | Works | |
| `/submissions/[id]` | Works | Back button links to `/submissions` |
| `/analytics` | Works | |
| `/knowledge` | Works | |
| `/revision` | Works | Topic filter is hardcoded (only 4 options) |
| `/settings` | Works | |
| `/connect` | Works | |
| `/auth/sign-in` | Demo-only | Shows "Demo mode" — no real auth |

**Dead links / hardcoded values:**
- `sidebar.tsx:196` — Hardcoded "63 documents" and "3d ago" in MemoryStatus
- `settings-view.tsx:340` — Hardcoded "63 documents indexed"
- `settings-view.tsx:275` — "Mock in this build" comment in Data & sync section
- `frontend/app/page.tsx:4` — `EVOLUTION_STORIES` hardcoded for landing page

**Back-navigation:**
- Submission detail back to submissions: OK
- Problem drawer close button: OK
- Revision "Open problem" link: OK

### B. Loading States

| Page | Loading | Empty | Error |
|------|---------|-------|-------|
| Dashboard | Skeleton | Per-section EmptyDataState | ErrorState, no retry |
| Problems | Skeleton | EmptyState | ErrorState, no retry |
| Submissions | Skeleton strip | EmptyState | ErrorState, no retry |
| Submission Detail | Skeleton | N/A | ErrorState |
| Analytics | Skeleton | Per-section EmptyDataState | ErrorState |
| Knowledge | Skeleton | EmptyDataState | ErrorState |
| Search | Skeleton rows | EmptyState | Inline error |
| Revision | Skeleton strip | EmptyState + refresh | ErrorState + retry |
| Settings | N/A (no loading indicator) | N/A | Error swallowed silently |
| Connect | Phase panels | N/A | ErrorRow |

**P2 — Settings loading:** No loading state shown while fetching initial settings; provider seeds from localStorage then fetches, but `isLoading` is never consumed by the UI.

### C. Empty States

All `/(app)/` pages have proper empty states. The landing page (`/app/page.tsx`) does NOT — it always renders mock data regardless of whether the backend has real data.

### D. Error States

| Page | Backend down | 404 | 500 | Network error | Malformed | Retry? |
|------|-------------|-----|-----|--------------|-----------|--------|
| Dashboard | Shows error | Shows error | Shows error | Shows error | Shows error | No |
| Problems | Shows error | Shows error | Shows error | Shows error | Shows error | No |
| Submissions | Shows error | Shows error | Shows error | Shows error | Shows error | No |
| Submission Detail | Shows error | Shows error | Shows error | Shows error | Shows error | No |
| Analytics | Shows error | Shows error | Shows error | Shows error | Shows error | No |
| Knowledge | Shows error | Shows error | Shows error | Shows error | Shows error | No |
| Search | Shows error | N/A | Shows error | Shows error | Shows error | No |
| Revision | Shows error | Shows error | Shows error | Shows error | Shows error | Yes |
| Settings | Silently uses defaults | N/A | N/A | N/A | N/A | No |
| Connect | Shows error | N/A | Shows error | Shows error | Shows error | Yes (re-navigate) |

**P2 — Settings error swallowing:** The provider catches errors and stores them in `error` state, but `settings-view.tsx` never reads `error` from context. User gets no feedback when settings can't be saved.

---

## E. Mock Data Audit

| File | Classification | Notes |
|------|---------------|-------|
| `frontend/app/page.tsx` | MOCK (P2) | Landing page uses getDashboardData, getMockProblems, getEvolutionStory |
| `frontend/lib/data.ts` | MOCK (P2) | Data seam that delegates to mock functions |
| `frontend/lib/mock/problems.ts` | MOCK (P2) | 47 curated problems, deterministic RNG |
| `frontend/lib/mock/analytics.ts` | MOCK (P2) | Derives analytics from mock problems |
| `frontend/lib/mock/activity.ts` | MOCK (P2) | Activity heatmap and timeline from mock data |
| `frontend/lib/mock/knowledge.ts` | MOCK (P2) | Knowledge graph from mock problems |
| `frontend/lib/mock/revision.ts` | MOCK (P2) | Revision queue computation mirrors backend |
| `frontend/lib/mock/snippets.ts` | PLACEHOLDER (P2) | Real solution code for 3 problems, no backend endpoint |
| `frontend/lib/mock/derive.ts` | DERIVED (OK) | Pure helpers, used by real API-driven components |
| `frontend/lib/mock/clock.ts` | PLACEHOLDER (P2) | Mock date functions for deterministic timestamps |
| `frontend/lib/mock/random.ts` | MOCK (P2) | Deterministic RNG for mock data |
| `frontend/components/app/sidebar.tsx:196` | MOCK (P3) | Hardcoded "63 documents", "3d ago" |
| `frontend/app/(app)/dashboard/page.tsx:24` | PLACEHOLDER (P2) | getEvolutionStory("3sum") — no backend endpoint |
| `frontend/components/app/knowledge/knowledge-graph.tsx` | DERIVED (OK) | Layout/rendering only — operates on API data |

**P1 — Sidebar MemoryStatus:** Shows hardcoded "63 documents" and "3d ago" instead of calling the memory stats API endpoint. This is fabricated data shown in the production UI shell.

---

## F. Account Isolation Matrix

| Feature | Account-scoped? | Backend Enforcement | Notes |
|---------|----------------|-------------------|-------|
| Dashboard | Yes | Yes | active_account passed to all analytics |
| Problems | Yes | Yes | list_problems() scopes internally |
| Problem Detail | Yes | Yes | get_problem(slug, account=active_account) |
| Submissions | Yes | Yes | _get_all_submissions filters by source_account |
| Submission Detail | Yes | Yes | get_submission(id, account=active_account) |
| Search | Yes | Yes | global_search → list_problems scoping |
| Knowledge | Yes | Yes | get_knowledge_graph(account=...) |
| Revision Queue | Yes | Yes | get_revision_queue(account=active_account) |
| Memory Search | Yes | Yes | memory_search(account=active_account) |
| Similar Problems | Yes | Yes | memory_find_similar_problem(account=...) |
| Common Mistakes | Yes | Yes | memory_find_common_mistakes(account=...) |
| Previous Approaches | Yes | Yes | memory_find_previous_approaches(account=...) |
| Semantic Search | No | No | semantic_search does NOT accept account param — P1 |
| revision.mark_reviewed | No | No | mark_reviewed does NOT accept account param — P1 |
| revision.get_problem_priority | No | No | Uses storage.get_by_slug directly — P1 |
| revision.get_due_problems | No | No | Calls get_revision_queue without account — P1 |

**P1 — Semantic Search:** The `CodeMemoryService.semantic_search()` method at `service.py:788` does not accept or pass an `account` parameter. It calls `self.storage.list_all()` without filtering by account, which could expose another account's data.

**P1 — revision.mark_reviewed:** Called from `revision.py:33` route without account context. The method directly accesses `self.storage.get_by_slug()` without account filtering. While `mark_reviewed` only updates `updated_at` and adds a note, the lack of account scoping is a data integrity risk.

**P1 — revision.get_problem_priority:** Directly calls `self.storage.get_by_slug()` without account filtering at `revision_service.py:31`. This is called from the route handler chain.

**P1 — revision.get_due_problems:** At `revision_service.py:167`, calls `self.get_revision_queue(limit=100)` without passing the account parameter, even though `get_revision_queue` accepts it.

---

## G. API Consistency

| Endpoint | Method | Status | Error DTO | camelCase | Notes |
|----------|--------|--------|-----------|-----------|-------|
| /health | GET | 200 | Consistent | Yes | |
| /dashboard | GET | 200 | Consistent | Yes | |
| /problems | GET | 200 | Consistent | Yes | Query: page_size (snake_case) |
| /problems/{slug} | GET | 200, 404 | Consistent | Yes | |
| /problems/{slug}/evolution | GET | 200, 404 | Consistent | Yes | |
| /submissions | GET | 200 | Consistent | Yes | Query: page_size (snake_case) |
| /submissions/{id} | GET | 200, 404 | Consistent | Yes | |
| /analytics | GET | 200 | Consistent | Yes | Query: granularity |
| /knowledge | GET | 200 | Consistent | Yes | |
| /revision | GET | 200 | Consistent | Yes | Query: limit, topic |
| /revision/{slug}/reviewed | POST | 200, 400, 404 | Inconsistent | Yes | 500s reported as 404 |
| /leetcode/status | GET | 200 | Consistent | Yes | |
| /leetcode/connect | POST | 200, 422, 503 | Consistent | Yes | |
| /leetcode/sync | POST | 200, 400, 500 | Consistent | Yes | |
| /leetcode/connect | DELETE | 200 | Consistent | Yes | |
| /settings | GET | 200 | Consistent | Yes | |
| /settings | PUT | 200 | Consistent | Yes | P2: PUT for partial updates — PATCH is REST convention |
| /search | GET | 200 | Consistent | Yes | Query: q, limit |

The `BaseCamelModel` uses `alias_generator=to_camel` with `populate_by_name=True`. FastAPI respects response_model aliases automatically, so API responses use camelCase fields. This is consistent throughout.

---

## H. Backend Architecture

### P2 — Dead Code: service.py:193-210

```python
        return unscoped
        # DEAD CODE — never reached
        for p in all_problems:
            kept_attempts = []
            ...
```

Lines 194-210 are unreachable code duplicated from the account-filtered branch above.

### P2 — Direct storage access in revision_service.py

`revision_service.py` methods bypass `CodeMemoryService.list_problems()` account scoping:
- `get_problem_priority()` (line 31): `self.storage.get_by_slug(identifier)` — no account filter
- `mark_reviewed()` (line 173): `self.storage.get_by_slug(identifier)` — no account filter

### P3 — Broad exception handling in leetcode.py:38,59

```python
    except Exception as e:
        raise HTTPException(status_code=503, detail="Unable to connect to LeetCode right now.")
```

These catch-all handlers mask real bugs. The `safe_error_message` import at line 5 is unused in the connect handler.

### P3 — Inconsistent lifecycle in revision_service.py:167

`get_due_problems` calls `self.get_revision_queue(limit=100)` without passing `account`, even though the method signature accepts it.

---

## I. Frontend API Layer

### All `/(app)/` pages correctly use:
1. `frontend/lib/api/client.ts` — centralized fetch wrapper
2. `frontend/lib/api/resources.ts` — typed API functions
3. `frontend/lib/api/mappers.ts` — DTO mapping

No direct `fetch()` calls exist outside this layer.

### Issues:

**P1 — Duplicate data layer:** `frontend/lib/data.ts` coexists with `frontend/lib/api/`. The landing page (`app/page.tsx`) uses the mock layer exclusively. If this layer is used by any authenticated route, it would bypass API error handling entirely.

**P3 — Unused schema types:** `SearchResultProblem` and `SearchResultSubmission` in `schemas/problems.py:92-110` are defined but never used — the search endpoint uses generic `SearchResultItem` with a metadata dict.

---

## J. Persistence

| Feature | Storage | Backend | Status |
|---------|---------|---------|--------|
| Settings | JSON file | SettingsStore → app_settings.json | OK |
| LeetCode account | JSON file | AccountService → accounts/ | OK |
| Problem/submission data | DuckDB + Parquet | CompositeStorage | OK |
| Memory index | DuckDB + SemanticIndex | MemoryEngine | OK |
| Sidebar collapse | localStorage | N/A (UI-only) | OK |
| Theme preference | localStorage seed → backend | SettingsStore | OK |

**P3 — Settings "Data & sync" mock:** The settings-view.tsx Data & sync section has simulated import/rebuild actions with hardcoded responses. Comment at line 275 says "Mock in this build."

---

## Bugs Found by Priority

### P0
1. None found

### P1
1. **Semantic search not account-scoped** — `CodeMemoryService.semantic_search()` at `service.py:788` does not filter by account
2. **revision.mark_reviewed not account-scoped** — `revision_service.py:171` and route `revision.py:33` don't pass account
3. **revision.get_problem_priority not account-scoped** — `revision_service.py:31` uses `storage.get_by_slug()` without account filter
4. **Dead code after return** — `service.py:193-210`
5. **Duplicate data layer** — `frontend/lib/data.ts` exists alongside `frontend/lib/api/`
6. **Settings error swallowed** — Provider catches errors but UI never surfaces them

### P2
1. **Sidebar MemoryStatus hardcoded** — "63 documents", "3d ago" at `sidebar.tsx:196`
2. **revision.get_due_problems missing account** — `revision_service.py:167`
3. **mark_reviewed error handling misleading** — 500 reported as 404 at `revision.py:37`
4. **Settings PUT vs PATCH** — Uses PUT for partial updates
5. **Landing page uses mock data** — `frontend/app/page.tsx` shows fabricated data
6. **Settings "Data & sync" not wired** — Simulated actions in settings-view.tsx:271-357

### P3
1. **Broad exception catching** — leetcode.py:38,59
2. **Unused safe_error_message import** — leetcode.py:5
3. **Unused schema types** — schemas/problems.py:92-110
4. **Settings no loading state** — isLoading never consumed
5. **Topic filter hardcoded** — revision-workspace.tsx:47-53

---

## Files Changed
None — this is an audit-only report.

---

## Recommendations for Next Implementation Phase
1. Fix `service.py` dead code — remove lines 194-210
2. Add `account` parameter to `revision_service.mark_reviewed`, `get_problem_priority`, `get_due_problems`
3. Add `account` parameter to `CodeMemoryService.semantic_search()`
4. Update `revision.py` route to pass `account=service.active_account` to revision service calls
5. Remove hardcoded values from `sidebar.tsx` MemoryStatus — use API if available, or remove
6. Surface Settings errors in `settings-view.tsx`
7. Wire Settings "Data & sync" section to real backend or mark as not-yet-available
8. Replace `frontend/lib/data.ts` usage in landing page with API calls (or mark as demo)
9. Consider changing Settings PUT to PATCH for REST consistency
10. Add retry to data-driven pages
