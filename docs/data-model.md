# CodeMemory Data Model Documentation

CodeMemory represents a user's DSA problem-solving journey using strongly typed Pydantic v2 domain models.

```
Problem (1)
 ├──> Attempts (1..N)
 │      └──> Submissions (1..N)
 ├──> Notes (0..N)
 └──> SolutionAnalysis (0..1)
```

## Core Domain Entities

### 1. `Problem`
- `id`: Unique UUID identifier.
- `title`: Problem title (e.g. "Two Sum").
- `slug`: Human-readable URL slug (e.g. `two-sum`).
- `difficulty`: Enum (`EASY`, `MEDIUM`, `HARD`, `UNKNOWN`).
- `platform`: Enum (`LEETCODE`, `HACKERRANK`, `CODEFORCES`, `CUSTOM`).
- `topics`: List of topic strings (e.g. `["Array", "Hash Table"]`).
- `url`: Optional problem statement URL.
- `statement`: Problem text.

### 2. `Attempt`
- `id`: Attempt UUID.
- `problem_id`: Foreign key to `Problem`.
- `attempt_number`: Chronological 1-based attempt sequence number.
- `approach_summary`: High-level approach title (e.g. "Brute Force", "Two Pointers").
- `reasoning`: Detailed thought process explanation.
- `status`: Enum (`ACCEPTED`, `TIME_LIMIT_EXCEEDED`, `WRONG_ANSWER`, `MEMORY_LIMIT_EXCEEDED`, `UNKNOWN`).
- `mistakes`: List of identified logic or edge-case mistakes.

### 3. `Submission`
- `id`: Submission UUID.
- `problem_id`: Foreign key to `Problem`.
- `attempt_id`: Foreign key to `Attempt`.
- `code`: Raw source code snippet.
- `language`: Programming language identifier (`python`, `cpp`, `java`, etc.).
- `status`: `SubmissionStatus`.
- `runtime_ms`: Execution runtime in milliseconds.
- `memory_mb`: Memory consumption in MB.
- `submission_hash`: Deterministic SHA-256 string for idempotency check.
