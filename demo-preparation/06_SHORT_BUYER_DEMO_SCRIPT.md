# Short buyer-facing demo script

## Recommendation

The intended cut is **4–5 minutes**, but the current build is **not ready for a buyer-facing functional demo**. It supports a truthful preview tour only. Do not represent preview data as actual records or claim the end-to-end workflow works. Record this cut only after synthetic seeding and blockers in report 08 are resolved.

### 1. Product premise (0:45)

**Start:** `http://127.0.0.1:3000/`, hero visible. **Action:** Point to `PRODUCT PREVIEW · EXAMPLE DATA`; scroll to “Every attempt is preserved.” **Say:** “CodeMemory is a local-first DSA memory system. It preserves the reasoning and attempts behind a solution, then makes that history useful for search, revision, and progress analysis. The landing page is an illustrative preview; the workspace reads from a local API.” **Verify:** Example disclosure visible. **Avoid:** Quoting preview totals as real records.

### 2. Live local dashboard (0:45)

**Start:** Fresh seeded API is healthy; open `/dashboard`. **Action:** Show actual positive counts and identify the evolution card as illustrative. **Say:** “This is the local workspace. These counts should match the synthetic recording dataset. The evolution card is still explicitly marked as an example.” **Verify:** Counts agree with Problems/Submissions. Audit showed zeros; positive flow is unverified.

### 3. One complete DSA history (1:30)

**Start:** `/problems`, synthetic Two Sum row visible. **Action:** Search `Two Sum`, open record, show failed then accepted attempt and actual code/complexity/mistake fields. Only continue if detail and submissions load. **Say:** “The important unit is the sequence, not just the final accepted code. A reviewer can see what the earlier approach got wrong and what changed.” **Verify:** Attempt statuses match seed. `/submissions` currently crashes; wait for fix and retest.

### 4. What to revisit and what history says (1:15)

**Start:** `/revision`, then `/analytics`. **Action:** Show a queue explanation and two aggregate charts. Show AI/roadmap only after successful responses. **Say:** “The queue ranks work to revisit using recorded practice signals. Analytics summarizes the same history. I’m keeping this focused on values verified from indexed records.” **Verify:** Queue and analytics match submission data. Only empty states were observed; cards returned 404 in audit.

### 5. Local-first close (0:30)

**Start:** Dashboard, LeetCode disconnected. **Action:** Mention public profile path but leave it disconnected. **Say:** “The product is intended to turn an existing practice history into a personal reference system. This recording uses synthetic data and no real credentials.” **Verify:** No real handle or personal data is visible.

## If recording before blockers are resolved

Keep the cut to a preview-only concept tour, show the example-data disclosure, and say the live data workflow is still being prepared. Do not call it an end-to-end demo or validated product walkthrough.
