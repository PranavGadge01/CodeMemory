# CodeMemory 🧠

> **Local-first Personal Data Structures & Algorithms (DSA) Knowledge Engine**

CodeMemory is a local-first personal developer knowledge system designed to record, structure, search, and analyze your complete problem-solving journey for coding problems.

---

## 1. What CodeMemory Is
CodeMemory records your complete problem-solving evolution for Data Structures and Algorithms (DSA). For every problem, it stores problem metadata, submission attempts, raw source code, execution results (runtime/memory), reasoning, mistakes, time/space complexity analysis, and learning notes.

## 2. Why CodeMemory Exists
The goal of CodeMemory is **not** to build a generic LeetCode clone or CRUD dashboard.  
The goal is to build a **personal searchable knowledge system that remembers HOW you solved problems and how your thinking evolved over time**—from your initial brute-force attempt to your final optimal solution.

---

## 3. Core Features

- 🧠 **Thought Evolution Tracking**: Chronologically records every submission attempt, tracking how algorithm choice, runtime, and memory evolved over time.
- 🤖 **AI Solution Analysis**: Provides structured insights (inferred approach, algorithm design, Big-O complexity, key breakthroughs, and failure modes) with an offline rule-based heuristic fallback.
- 🔁 **Spaced Learning & Revision Engine**: Priority-scored queue recommending which problems to revisit based on difficulty, fail count, recency, and topic weakness.
- 🎯 **My Patterns (Personal DSA Memory)**: Automatically synthesizes your practice strengths, struggle areas, frequent mistakes, neglected topics, and language preferences.
- 🌐 **Lightweight Knowledge Graph**: Maps relationships between Topics, Problems, Approaches, Mistakes, and Languages without requiring complex external graph databases.
- 🔍 **Hybrid Multi-Criteria & Local Semantic Search**: Performs fast SQL metadata filtering and TF-IDF vector similarity search over code, notes, and mistakes.
- 📥 **Multi-Format Ingestion**: Idempotent bulk import supporting JSON, CSV, and JSONL data files with duplicate matching via SHA-256 hashes.
- 🖥️ **Streamlit Developer Studio**: Interactive local Web App with 12 dedicated views featuring Plotly visual charts and glassmorphism UI styling.

---

## 4. Architecture Overview

```
UI / CLI (Streamlit App & Rich CLI)
    ↓
CodeMemory Core & Services (Search, Revision, Analytics, AI, Graph, Importer, Exporter)
    ↓
Domain Models (Pydantic v2)
    ↓
Storage Interfaces (Repository Pattern)
    ↓
Composite Storage (Filesystem Markdown | Parquet Columnar | DuckDB Relational Engine)
```

---

## 5. Data Model

The core domain model consists of strongly typed entities:
- **`Problem`**: Holds metadata, title, slug, difficulty, platform, topics, and statement.
- **`Attempt`**: Groups submissions under a specific approach, tracking approach summary, reasoning, time/space complexity, and mistakes.
- **`Submission`**: Captures raw code, language, status (`Accepted`, `Time Limit Exceeded`, `Wrong Answer`), runtime, memory, and SHA-256 submission hash.
- **`SolutionAnalysis`**: Stores AI/heuristic structured analysis metadata.

---

## 6. Storage Design & Multi-Tier Strategy

CodeMemory uses a **Composite Storage Coordinator** that atomically synchronizes three storage formats:

```
                  ┌────────────────────────┐
                  │ Composite Storage      │
                  └───────────┬────────────┘
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ Filesystem       │ │ Parquet          │ │ DuckDB           │
│ Markdown KB      │ │ Columnar Engine  │ │ Relational Index │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

---

## 7. Why DuckDB?
DuckDB provides high-performance SQL query indexing, relational joins, and analytics on local data files with zero database server setup or configuration overhead.

## 8. Why Parquet?
Parquet columnar storage (powered by Polars) allows fast analytical scans over massive historical submission datasets with optimal disk compression.

## 9. Why Markdown?
Markdown knowledge files (`knowledge/<problem-slug>/problem.md`) make your personal developer knowledge base 100% human-readable, Git-friendly, and portable without vendor lock-in.

---

## 10. Analytics Engine
Calculates 14+ practice metrics including total problems, attempt distribution, acceptance rates, difficulty/topic distributions, solving velocity, and struggle problem identification.

## 11. Revision Engine
Calculates a deterministic priority score ($P$) for spaced revision:
$$P = W_{\text{diff}} \cdot S_{\text{diff}} + W_{\text{fail}} \cdot S_{\text{fail}} + W_{\text{recency}} \cdot S_{\text{recency}} + W_{\text{weakness}} \cdot S_{\text{weakness}} - W_{\text{recent\_solved}} \cdot S_{\text{recent\_solved}}$$

## 12. AI Code Analysis & Solution Evolution (Phase 6)

CodeMemory includes an optional, local-first AI intelligence layer that analyzes the user's **ACTUAL** submission attempts and historical solving process.

- 🤖 **Single Submission Analysis**: Ingresses source code, language, runtime, memory, and status to infer approach, algorithm design, Big-O complexities, potential edge-case bugs, and certain facts vs. likely explanations.
- 🧬 **Solution Evolution Analysis**: Traces how your code evolved across attempt 1 (e.g. Brute Force TLE) to attempt 2 (HashMap WA) to attempt 3 (Accepted optimal).
- 🧠 **Ask CodeMemory**: Natural language Q&A page grounded strictly in your personal DSA records.
- ⚡ **Deterministic Caching & Versioning**: Caches identity by `(submission_id, code_hash, version)` in `ai_analyses.parquet` to avoid duplicate API calls.
- 🔒 **Privacy & Offline Default**: Operates 100% offline using `HeuristicAIProvider` when no `OPENAI_API_KEY` is provided or when `AI_ENABLED=false`. Source code and user data remain 100% untouched.

See [docs/ai-architecture.md](docs/ai-architecture.md) for full architecture details.

## 13. Personal Semantic Memory Engine (Phase 7)

CodeMemory includes a local-first **Personal Semantic Memory Engine** that converts raw historical records into searchable memory documents (`MemoryDocument`) with strict provenance.

- 🧠 **Unified Memory Model**: Extracts memory documents for Problems, Attempt Reasonings, Code Submissions, Mistakes, Notes, and AI Analyses.
- ⚡ **Local Incremental Vector Index**: Stores embeddings in `data/memory_embeddings.parquet`. Skips unaltered records using SHA-256 content hashes (`content_hash`).
- 🔎 **Hybrid Retriever**: Combines vector cosine similarity ($0.5$), keyword match ($0.3$), and structured criteria ($0.2$).
- 🔗 **Similar Problem Discovery**: Recommends related problems explaining *why* they are similar (shared topics, patterns, structural complexity).
- 📜 **Historical Mistake & Evolution Tracking**: Tracks actual failure evidence and attempt progressions (Attempt 1 TLE → Attempt 2 WA → Attempt 3 Accepted).

See [docs/memory-architecture.md](docs/memory-architecture.md) for full memory engine documentation.

---

## 14. Installation & Setup

```bash
git clone https://github.com/your-username/codememory.git
cd codememory

# Install package with development dependencies
pip install -e .[dev]
```

---

## 15. Usage & Commands

```bash
# Launch Streamlit Developer Studio
codememory ui

# Seed database with 22 classic DSA problems
codememory seed

# Index memory documents incrementally
codememory memory index

# Rebuild semantic vector index
codememory memory rebuild

# Perform hybrid semantic search
codememory memory search "sliding window"

# Recommend similar problems
codememory memory similar two-sum

# Show historical mistake records
codememory memory mistakes

# Display personal memory statistics
codememory memory stats

# View problem details
codememory problem two-sum

# Trace problem evolution history
codememory history two-sum

# View personal DSA patterns summary
codememory patterns

# View knowledge graph summary
codememory graph

# Export Git-friendly Markdown knowledge base
codememory export
```

---

## 16. LeetCode Integration (Phase 5)

CodeMemory can import your LeetCode history as a **local-first, privacy-preserving dataset**. No passwords, cookies, or API keys required.

### Supported Import Formats

**JSON** (recommended):
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
    "code": "class Solution:\n    def twoSum(self, nums, target):\n        seen = {}\n        for i, n in enumerate(nums):\n            diff = target - n\n            if diff in seen:\n                return [seen[diff], i]\n            seen[n] = i"
  }
]
```

**CSV**: Upload a CSV with header row. Column aliases like `Problem Title`, `lang`, `status_display`, `Runtime`, `Submission ID` etc. are auto-recognized.

### LeetCode CLI Commands

```bash
# Validate dataset (dry run, no data stored)
codememory leetcode validate path/to/data.json

# Preview import statistics
codememory leetcode preview path/to/data.json

# Import idempotently (safe to run multiple times)
codememory leetcode import path/to/data.json

# CSV is also supported
codememory leetcode import path/to/data.csv
```

### LeetCode UI Import

Launch the Streamlit app and navigate to **Import**. Select `LeetCode Export Dataset` as the source type, upload your file, and review the preview before confirming import.

### Normalization

- Status strings (`Accepted`, `Wrong Answer`, `TLE`, `WA`, `ac`, numeric codes) → `SubmissionStatus` enum
- Language strings (`python3`, `cpp`, `golang`, `javascript`) → standardized names
- Timestamps (epoch seconds, epoch ms, ISO strings) → UTC datetime
- Difficulty strings → `Easy`/`Medium`/`Hard`

### Deduplication

CodeMemory never imports the same submission twice:
1. **Primary key**: `leetcode_<submission_id>` when present
2. **Fallback hash**: `SHA-256(slug + timestamp + language + status + code)` for records without IDs

Running `leetcode import` on the same file twice imports 0 new records.

### All Attempts Preserved

Failed submissions (Wrong Answer, TLE, MLE) are **permanently preserved** alongside the accepted solution:

```
Two Sum
  Attempt 1 — Wrong Answer (python3)
  Attempt 2 — Time Limit Exceeded (python3)
  Attempt 3 — Accepted ✓ (python3)
```

This enables full chronological evolution tracking in analytics, revision, and the problem detail UI.

See [docs/leetcode-integration.md](docs/leetcode-integration.md) for full documentation.

---

## 17. Import Schema Formats

Supports JSON, CSV, and JSONL data files:

```json
[
  {
    "title": "3Sum",
    "difficulty": "Medium",
    "topics": ["Array", "Two Pointers"],
    "language": "python",
    "code": "def threeSum(nums): pass",
    "status": "Accepted",
    "runtime": "180 ms",
    "memory": "19.5 MB"
  }
]
```

---

## 18. Example Workflow

1. Import your historical submissions: `codememory import my_data.json`
2. Or import from LeetCode: `codememory leetcode import my_leetcode.json`
3. Launch the Web Studio: `codememory ui`
4. Inspect solution evolution and AI analysis for complex problems.
5. Check your **Revision Queue** to practice due problems.
6. Review **My Patterns** to target weak DSA topics.

---

## 19. Development
- Clean layered architecture under `src/codememory/`.
- Strict typing with Pydantic v2.
- Configurable environment options via `.env`.

---

## 20. Running Automated Tests

```bash
# Run complete pytest test suite
pytest -v

# Run with test coverage report
pytest --cov=codememory
```

---

## 21. Future Roadmap

- 📱 Mobile-responsive web views and offline PWA integration.
- ⚡ Expanded IDE extensions (VS Code plugin for one-click submission logging).
- 🔗 Graphviz / D3 interactive visual knowledge graph rendering.
- 🤝 LeetCode real-time sync via authenticated GraphQL session (extension point prepared in `LeetCodeClient`).

---

## License

MIT License.
