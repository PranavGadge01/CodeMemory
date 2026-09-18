# LeetCode Integration Guide

## Overview

CodeMemory's LeetCode integration provides a safe, import-first pipeline that transforms your LeetCode history into the CodeMemory knowledge system.

```
LeetCode (Export / API)
        ↓
LeetCodeParser (JSON / CSV)
        ↓
LeetCodeMapper (Normalization)
        ↓
LeetCodeImporter (Validation + Deduplication)
        ↓
CodeMemory Core (ImportService)
        ↓
CompositeStorage (DuckDB + Parquet + Markdown)
        ↓
Analytics / Search / Patterns / Revision / UI
```

---

## Supported Input Formats

### JSON Format (Recommended)

Arrays of submission objects exported from LeetCode or tools that generate LeetCode-compatible JSON:

```json
[
  {
    "submission_id": "1003",
    "title": "Two Sum",
    "title_slug": "two-sum",
    "difficulty": "Easy",
    "topics": ["Array", "Hash Table"],
    "language": "python3",
    "status": "Accepted",
    "runtime": "45 ms",
    "memory": "17.2 MB",
    "timestamp": 1700007200,
    "url": "https://leetcode.com/problems/two-sum/",
    "code": "class Solution:\n    def twoSum(self, nums, target):\n        seen = {}\n        for i, n in enumerate(nums):\n            diff = target - n\n            if diff in seen:\n                return [seen[diff], i]\n            seen[n] = i"
  },
  {
    "submission_id": "1002",
    "title": "Two Sum",
    "title_slug": "two-sum",
    "difficulty": "Easy",
    "topics": ["Array", "Hash Table"],
    "language": "python3",
    "status": "Time Limit Exceeded",
    "timestamp": 1700003600,
    "code": "class Solution:\n    def twoSum(self, nums, target):\n        for i in range(len(nums)):\n            for j in range(len(nums)):\n                if i != j and nums[i] + nums[j] == target:\n                    return [i, j]"
  }
]
```

### CSV Format

CSV with header row. Recognized column names:

| Column Name    | Aliases                                                | Notes                              |
|----------------|--------------------------------------------------------|------------------------------------|
| `title`        | `Problem Title`, `problem_title`, `Question Title`     | Required                           |
| `language`     | `lang`, `Language`                                     | Required                           |
| `status`       | `Status`, `Result`, `status_display`                   | Required                           |
| `code`         | `source_code`, `Code`, `Source Code`                   | Optional but recommended           |
| `submission_id`| `id`, `Submission ID`                                  | Optional                           |
| `difficulty`   | `Difficulty`, `Level`                                  | Optional                           |
| `topics`       | `Topics`, `tags`, `Tags`, `topic_tags`                 | Comma-separated string or list     |
| `runtime`      | `Runtime`, `Execution Time`                            | e.g. `"45 ms"`                     |
| `memory`       | `Memory`, `Memory Usage`                               | e.g. `"17.2 MB"`                   |
| `timestamp`    | `Date`, `submitted_at`, `created_at`                   | Epoch seconds, ISO string, or int  |

---

## Status Normalization

LeetCode raw status strings are normalized to CodeMemory `SubmissionStatus` enum values:

| LeetCode Status        | Aliases              | CodeMemory Value          |
|------------------------|----------------------|---------------------------|
| `Accepted`             | `ac`, `10`           | `ACCEPTED`                |
| `Wrong Answer`         | `wa`, `11`           | `WRONG_ANSWER`            |
| `Time Limit Exceeded`  | `tle`, `12`          | `TIME_LIMIT_EXCEEDED`     |
| `Memory Limit Exceeded`| `mle`, `13`          | `MEMORY_LIMIT_EXCEEDED`   |
| `Runtime Error`        | `re`, `14`           | `RUNTIME_ERROR`           |
| `Compile Error`        | `ce`, `15`           | `COMPILE_ERROR`           |

---

## Language Normalization

| LeetCode Value | Normalized Value |
|----------------|-----------------|
| `python3`      | `Python`        |
| `python`       | `Python`        |
| `cpp`          | `C++`           |
| `java`         | `Java`          |
| `golang`       | `Go`            |
| `javascript`   | `JavaScript`    |
| `typescript`   | `TypeScript`    |
| `rust`         | `Rust`          |
| `csharp`       | `C#`            |
| `kotlin`       | `Kotlin`        |
| `swift`        | `Swift`         |
| `ruby`         | `Ruby`          |

---

## Timestamp Parsing

Timestamps are parsed in the following priority order:

1. **Epoch seconds** (e.g. `1700007200`) — automatically detected if value > 0 and < `1e11`
2. **Epoch milliseconds** (e.g. `1700007200000`) — detected if value > `1e11`, divided by 1000
3. **ISO 8601 string** (e.g. `"2026-09-06T10:00:00Z"` or `"2026-09-06T10:00:00+05:30"`)
4. **Common date strings** (`"2026-09-06 10:00:00"`, `"2026-09-06"`)
5. **Fallback**: current UTC timestamp

All timestamps are stored in UTC internally.

---

## Deduplication Strategy

CodeMemory uses a **two-tier deduplication system** to ensure the same submission is never imported twice.

### Tier 1: External Submission ID (Primary)
If `submission_id` is available, it is prefixed with `"leetcode_"` and used as the canonical ID:
```
external_id = "leetcode_<submission_id>"
```
Example: `"leetcode_1003"`

### Tier 2: Deterministic SHA-256 Hash (Fallback)
If no `submission_id` is present, a deterministic fingerprint hash is computed:
```python
fingerprint = f"{problem_slug}:{timestamp}:{language}:{status}:{code.strip()}"
hash = SHA256(fingerprint)
```

This hash is stored in `submission_hash` on the `Submission` domain model and checked before every import.

### Behavior

| Import              | Expected Result                          |
|---------------------|------------------------------------------|
| First import        | All records imported                     |
| Same dataset again  | 0 new records (all duplicates detected)  |
| New submissions added | Only net-new submissions imported      |

---

## Incremental Import

CodeMemory fully supports incremental imports from growing LeetCode datasets.

**Example workflow:**

```bash
# Day 1: 100 submissions
python -m codememory.cli.main leetcode import day1_data.json
# → Imported: 100 submissions

# Day 2: 110 submissions (10 new)
python -m codememory.cli.main leetcode import day2_data.json
# → Imported: 10 submissions (100 duplicates skipped)
```

Import statistics reported:
- `total_read`: total records in file
- `valid_count`: records passing schema validation
- `imported_count`: net-new records stored
- `duplicate_count`: records already in storage (skipped)
- `error_count`: records failing validation
- `imported_problems`: list of affected problem slugs

---

## Knowledge File Generation

After import, CodeMemory automatically generates or updates Markdown knowledge files for each imported problem:

```
knowledge/
    two-sum/
        problem.md        ← Problem metadata and description
        attempts.md       ← Chronological attempt history
        metadata.json     ← Machine-readable metadata
        solution.py       ← Latest accepted solution source
```

### Preservation Guarantee
Importing new submissions for an existing problem **never overwrites** previous attempt history. All attempts are preserved in chronological order in `attempts.md`.

---

## CLI Commands

```bash
# Validate a LeetCode dataset file (no data stored)
python -m codememory.cli.main leetcode validate path/to/data.json

# Preview import statistics without committing
python -m codememory.cli.main leetcode preview path/to/data.json

# Import LeetCode dataset idempotently
python -m codememory.cli.main leetcode import path/to/data.json

# CSV files are also supported
python -m codememory.cli.main leetcode import path/to/data.csv
```

---

## UI Import

Open the Streamlit application and navigate to **Import**:

1. Select **"LeetCode Export Dataset (JSON / CSV)"** as source type
2. Upload your LeetCode JSON or CSV file
3. Review the validation preview (problems, submissions, duplicates, errors)
4. Click **"Confirm & Import LeetCode Dataset"**

---

## Privacy & Security

CodeMemory is **local-first** by design. It stores **zero** of the following:
- LeetCode passwords
- Session cookies
- Authentication tokens
- API credentials

All data stays in your local `data/` directory. No network connections are made during import-based workflows.

---

## Known Limitations

1. **No live synchronization**: Phase 5 implements safe file-based import only. Real-time LeetCode sync requires a session cookie or OAuth mechanism not yet implemented.
2. **No problem statement import**: LeetCode problem statements are copyrighted and are not parsed from exported data. The `problem.md` description field will be empty unless you manually add it.
3. **Code availability**: Submitted code is only included if your export tool captures it. Many LeetCode export tools capture only metadata, not source code.
4. **CSV encoding**: CSV files must be UTF-8 encoded.

---

## Future Live Sync Architecture

The connector is architecturally prepared for live LeetCode synchronization. The `LeetCodeClient` class in `src/codememory/connectors/leetcode/client.py` implements the GraphQL API interface:

```python
class LeetCodeClient:
    def __init__(self, session_cookie: Optional[str] = None): ...
    def execute_query(self, query: str, variables: dict) -> dict: ...
    def fetch_user_submissions(self, username: str, limit: int) -> list: ...
    def fetch_problem_details(self, problem_slug: str) -> LeetCodeProblemRaw: ...
```

When an official LeetCode API or session-based mechanism becomes available, only `LeetCodeClient` needs updating. The rest of the pipeline (mapper → importer → core) remains unchanged.

---

## Testing

Run the full test suite including LeetCode integration tests:

```bash
python -m pytest -v
```

Key test files:
- `tests/test_leetcode_connector.py`: Parser, mapper, client unit tests
- `tests/test_leetcode_import.py`: End-to-end import, deduplication, incremental import
- `tests/fixtures/leetcode/sample_leetcode.json`: Realistic JSON fixture (3 problems, 6 submissions)
- `tests/fixtures/leetcode/sample_leetcode.csv`: CSV fixture (2 problems, 2 submissions)
