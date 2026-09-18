# CodeMemory Data Model

The CodeMemory domain model captures the full problem-solving journey rather than static code snippets.

## Entity Relationships

```
Problem (1)
 └── (Many) Attempts
      └── (Many) Submissions
 └── (Many) Notes
```

### 1. Problem
Represents a unique algorithmic problem.
- `id` (UUID string)
- `title` (str)
- `slug` (str, e.g. `two-sum`)
- `difficulty` (`Easy` | `Medium` | `Hard` | `Unknown`)
- `platform` (`LeetCode` | `HackerRank` | `Codeforces` | `Custom`)
- `url` (optional string)
- `topics` (list of strings)
- `statement` (optional markdown text)
- `created_at`, `updated_at` (datetime)

### 2. Attempt
Represents an approach or session solving a problem.
- `id` (UUID string)
- `problem_id` (UUID string)
- `attempt_number` (int)
- `approach_summary` (str, e.g. "Hash Map Lookups")
- `reasoning` (optional text)
- `mistakes` (list of strings)
- `analysis` (SolutionAnalysis object: time/space complexity, key insights)
- `status` (`Accepted` | `Wrong Answer` | `Time Limit Exceeded` | etc.)
- `submissions` (list of Submissions)

### 3. Submission
An execution record of source code against tests.
- `id` (UUID string)
- `problem_id` (UUID string)
- `attempt_id` (UUID string)
- `code` (str)
- `language` (str, e.g. `python`, `cpp`, `java`)
- `status` (`SubmissionStatus` enum)
- `runtime_ms` (optional float)
- `memory_mb` (optional float)
- `submitted_at` (datetime)
- `submission_hash` (deterministic SHA256 string for idempotency)

### 4. ProblemNote
Human notes, intuition logs, or bug pattern records.
- `id` (UUID string)
- `problem_id` (UUID string)
- `content` (str)
- `note_type` (`Intuition` | `Bug Pattern` | `Complexity Analysis` | `General`)
