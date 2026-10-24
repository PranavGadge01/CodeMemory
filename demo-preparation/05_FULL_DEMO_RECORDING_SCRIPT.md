# Full demo recording script

## Recording gate

Recommended eventual duration: **15–20 minutes**, including the import-first Python studio flow and the newer Next workspace, after seeded positive paths are verified. **Do not record this as a completed-product walkthrough yet.** The audited runtime had an empty API dataset, `/submissions` crashed, analytics learning/insight cards returned HTTP 404, Python tests could not run, and frontend checks fail. The script separates truthful preview content from gated workflows.

Start only after the preflight in `02_RUN_AND_TEST_GUIDE.md` passes, especially positive seeded views and current build/runtime checks. Until then, the short cut can only be a preview, clearly naming sample data.

### Segment 1 — Introduce the problem and product (1:00)

**Starting state:** Browser at `http://127.0.0.1:3000/`, top of page.

**Actions:** Pause at hero; point to `PRODUCT PREVIEW · EXAMPLE DATA`. Scroll to “Every attempt is preserved,” then use “Open CodeMemory” to enter `/dashboard`.

**Say:** “CodeMemory is a local-first memory layer for DSA practice. The idea is to keep the attempts and reasoning around a solution, then use that history for search, revision, and analytics. This first page is a product preview with example data; I’ll move into the workspace for the live local index.”

**Visible result / verification:** Product positioning and example-data disclosure. The page was browser verified; sample metrics are illustrative only.

**Avoid showing:** Presenting preview totals as a real account or backend data.

**Transition:** Click “Open CodeMemory.” **Recovery:** If the page fails, stop and restore service; do not substitute screenshots. **Status:** PASS for preview rendering only.

### Segment 2 — Import a synthetic DSA history (2:00)

**Starting state:** Isolated Streamlit studio at `http://127.0.0.1:8501`, launched with `demo-preparation/streamlit-profile` as its working directory. The profile is fresh and LeetCode is not connected. The file to select is the repository’s synthetic fixture at `tests/fixtures/leetcode/sample_leetcode.json` (six sample submissions).

**Actions:** In the sidebar choose **Data Import**. Select **LeetCode Export Dataset (JSON / CSV)**. Use the upload control to select `sample_leetcode.json`. Pause on **LeetCode Normalization & Validation Preview** and verify record counts/errors before clicking **Confirm & Import LeetCode Dataset** once. Wait for the import-complete message and the rerun to settle.

**Say:** “This import is local and uses a repository test fixture, not a real LeetCode account. CodeMemory normalizes the fields and previews the records before I confirm. The saved history contains failed and accepted attempts that the other views can inspect.”

**Visible result / verification:** The preview names the parsed/valid records and import result; the studio should then show nonzero problems. The source defines these labels and the synthetic fixture, but this interaction was not runtime tested because Python could not run.

**Avoid showing:** A personal export, an account username, credentials, or a successful-result claim unless the count and affected problems visibly match the fixture.

**Transition:** End this take after the success state. Stop Streamlit with `Ctrl+C`, then start API/frontend against the same `streamlit-profile/data` and `streamlit-profile/knowledge` paths using `02_RUN_AND_TEST_GUIDE.md`; record the Next workspace as a separate take. Do not run both apps against the DuckDB file at once.

**Recovery:** If preview shows validation errors or wrong counts, do not confirm. Stop and inspect the fixture/profile; choose a new profile for another attempt, not a destructive reset.

**Status:** NOT TESTED; source-defined workflow, gated on Python restoration.

### Segment 3 — Show the local workspace and data boundary (0:45)

**Starting state:** API healthy, seeded demo folder loaded, `/dashboard` opened once. Audited state was empty.

**Actions:** Show metric strip and sidebar index status. Confirm counts match the synthetic seed before recording.

**Say:** “The workspace reads from the local API and storage index. In this prepared profile, these counts should reflect the synthetic submissions we seeded. The separate evolution card is labeled as an example.”

**Visible result / verification:** Positive seeded counts agree with Problems/Submissions. Only zero-data dashboard was browser verified. **Avoid:** Developer tools, personal paths, real records, environment variables, illustrative story as user history. **Transition:** Open Problems. **Recovery:** If 0/network error/mismatch, stop and check API path and seed. **Status:** BLOCKED for positive flow.

### Segment 4 — Trace one problem’s attempts (2:00)

**Starting state:** `/problems`; synthetic Two Sum or 3Sum appears.

**Actions:** Search `Two Sum`; confirm count narrows. Open row using the actual detail affordance. Show problem metadata, attempt list, and code/notes. Select attempts chronologically if failed-to-accepted data exists.

**Say:** “The record keeps each submission as part of the learning trail. The accepted code is useful, but the failed attempt explains what changed and why the final approach was better. This is synthetic history so the demo does not expose a real person’s account.”

**Visible result / verification:** Details come from the live API and agree with seed. Audited app had 0/0, so detail was not tested. **Avoid:** Real user code/identifiers. **Transition:** Submission log. **Recovery:** If detail is empty, verify API/seed; do not call landing-page example live. **Status:** BLOCKED pending seed.

### Segment 5 — Follow failure to acceptance (1:30)

**Starting state:** `/submissions` with seeded records. Mandatory preflight: audited frontend crashed here.

**Actions:** Confirm table loads. Filter by problem `Two Sum`, show failed and later accepted submission. Open a detail and show synthetic code/runtime/memory if present. Clear filter and show totals.

**Say:** “The submission log is the event-level view behind problem history. It keeps failures and accepted runs together, so comparisons come from records rather than a hand-written story.”

**Visible result / verification:** Row data/totals agree with API and problem detail. Current UI fails on undefined `filterOptions.statusCounts`.

**Avoid:** Error overlay or unverified claims. **Transition:** `/revision`. **Recovery:** Stop the take; resolve API/DTO mismatch and retest. Do not edit crash into apparent success. **Status:** FAIL in audit; gated.

### Segment 6 — Explain what to review (1:30)

**Starting state:** `/revision`; synthetic queue populated.

**Actions:** Select top row and show priority explanation, topic/difficulty/failure/recency inputs. Keep read-only; do not click “reviewed” until its persisted transition has been tested.

**Say:** “The revision queue ranks what to revisit using recorded difficulty, failure history, recency, and topic weakness. A row should explain why it is here.”

**Visible result / verification:** Seeded problem and score breakdown; compare title/topics to detail. Audited runtime showed empty queue only. **Avoid:** Hard-coded example or unverified persistence. **Transition:** Search. **Recovery:** If empty with seed, refresh once, then check account/date scope without resetting. **Status:** PARTIAL empty state; positive scoring blocked.

### Segment 7 — Retrieve a past idea (1:15)

**Starting state:** `/search`, synthetic data loaded.

**Actions:** Enter an exact term present in seed, such as `Hash Table`; wait, open one result, verify destination. Optionally show a no-match result.

**Say:** “Search is intended to bring back prior problem, submission, or knowledge records. I’m using a phrase that exists in the synthetic history and checking it opens the source record.”

**Visible result / verification:** Positive result links to correct record. Audit verified only `sliding window` no-results on an empty index. **Avoid:** Treating no-results as evidence of retrieval quality. **Transition:** Analytics. **Recovery:** Confirm seed/index before proceeding. **Status:** PARTIAL.

### Segment 8 — Connect history to analytics (2:00)

**Starting state:** `/analytics`; seeded submissions produce nonzero statistics.

**Actions:** Show summary, progress, difficulty/topic/language charts, and struggles. Wait for learning cards. Include profile insight, next-problem, roadmap, and patterns only if each succeeds.

**Say:** “These aggregates are derived from indexed attempts. The charts show practice volume and result distribution. The cards below add interpretation and next steps; I’ll include them only when the API response succeeds.”

**Visible result / verification:** Compare totals to submissions. Audit showed zero metrics and four cards at HTTP 404. **Avoid:** Cards in loading/error state or claims of working AI. **Transition:** Knowledge. **Recovery:** Omit any failing card; these 404s must be resolved before this segment is recorded. **Status:** PARTIAL core empty view; FAIL learning cards.

### Segment 9 — Show the knowledge model (1:30)

**Starting state:** `/knowledge`; graph nodes populated.

**Actions:** Show graph counts; select problem then topic/approach node. Use zoom/fit only if labels remain legible. Verify detail panel relates to selected node.

**Say:** “The graph is a view over stored relationships among problems, topics, approaches, languages, and mistakes. I’m selecting a node to follow one connection back to practice history.”

**Visible result / verification:** Live graph data. Audit had 0 nodes; selection untested. **Avoid:** Landing-page mock graph as user data. **Transition:** Settings. **Recovery:** If empty despite seed, check endpoint/account scope. **Status:** PARTIAL.

### Segment 10 — Preferences and integration boundary (1:00)

**Starting state:** `/settings`, isolated profile, LeetCode disconnected.

**Actions:** Show preference categories/status. Do not change settings. Note Codeforces/HackerRank “Coming soon.” Do not open credential controls.

**Say:** “This version is a local workspace, so there is no user login. Settings and LeetCode status come through the backend. Public sync is bounded and does not include source code or runtime; full-history sync is a separate credentialed path, so I’m leaving it disconnected.”

**Visible result / verification:** Preferences and integration state load; no write is made. **Avoid:** `.env`, keys, sessions, CSRF, vault files, personal handles. **Transition:** Dashboard recap. **Recovery:** If a real account appears connected, stop and switch to isolated data; do not disconnect it. **Status:** PARTIAL read-only.

### Segment 11 — Close with product value (0:45)

**Starting state:** Dashboard or preview with synthetic data and all cited flows verified.

**Actions:** Return dashboard; briefly point to verified problem count, attempts, queue, graph. End on workspace.

**Say:** “The product value is the connection between the record of an attempt and what you do next: keep the history, find it again, and use it to decide what to revisit. This walkthrough used synthetic local data; no account credentials or customer data were involved.”

**Visible result / verification:** Each cited feature passed earlier. Full sequence is not verified here. **Avoid:** Unverified metrics, 404 cards, broken submissions, logs. **Recovery:** Remove any claim whose feature failed and retake after resolution. **Status:** BLOCKED.

## Omit from this recording

- Real LeetCode connect/sync, authenticated credentials, account switching, or autosync.
- Import/deletion/reset controls; current frontend does not expose them and no destructive action is needed.
- AI cards until endpoints succeed.
- Submissions until crash is fixed and retested.
- CLI/Streamlit/Tauri until runtime setup and paths are verified.
