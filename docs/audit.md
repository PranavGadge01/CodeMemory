# CodeMemory — Repository Onboarding, Architecture Audit & Collaboration Preparation

You are joining an existing software project called **CodeMemory** as a new engineering agent/contributor.

Your first task is **NOT to immediately modify or rewrite code**.

Your first task is to deeply inspect the repository, understand what the project actually is, understand what has already been implemented, identify what is incomplete or broken, and produce a reliable technical map of the project so that future development can be done safely.

The repository itself is the **source of truth**.

Do not blindly trust README files, previous AI summaries, comments, TODOs, or documentation. Use them as context, then verify their claims against the actual implementation.

---

# 1. Project Context

CodeMemory is intended to be a:

> **Personal coding intelligence and learning system built around a developer's problem-solving history.**

The core idea is that instead of treating coding problems as isolated submissions, the system stores and analyzes the developer's historical:

* Problems
* Attempts
* Submissions
* Source code
* Runtime / memory
* Submission status
* Reasoning
* Mistakes
* Time/space complexity
* Learning notes
* Patterns
* Historical solution evolution

The system should turn this history into a persistent, searchable personal knowledge base.

The important conceptual pipeline is:

```text
Coding History
      ↓
Ingestion / Import
      ↓
Domain Models
      ↓
Storage
      ↓
 ┌──────────────┬──────────────┬──────────────┐
 ↓              ↓              ↓
Analytics      Memory         Graph
 ↓              ↓              ↓
Patterns       Embeddings     Relations
 ↓              ↓
Revision       Semantic Search
 └──────────────┬──────────────┘
                ↓
         Context Builder
                ↓
           AI Provider
                ↓
        Ask CodeMemory
```

The project is deliberately more than a CRUD dashboard or generic LeetCode clone.

---

# 2. Important Existing Architecture

The documented architecture currently appears to contain these major areas:

```text
src/codememory/

ai/
analytics/
app/
cli/
connectors/
core/
domain/
exporters/
graph/
ingestion/
memory/
patterns/
revision/
search/
storage/
```

The documented stack includes:

* Python
* Streamlit
* DuckDB
* Polars
* Parquet
* Pydantic v2
* Pytest
* GitHub Actions
* Docker
* Embeddings / semantic search
* OpenAI provider
* Heuristic/local AI fallback

The storage architecture is intended to abstract multiple persistence mechanisms:

```text
Repository abstraction
        │
 ┌──────┼────────┐
 ↓      ↓        ↓
DuckDB Parquet Filesystem
```

There is also a composite storage layer.

The AI architecture is intended to be provider-independent:

```text
AI Provider Interface
       │
 ┌─────┴──────────┐
 ↓                ↓
OpenAI       Heuristic/Fallback
```

The project also contains a LeetCode connector/import system, analytics, revision engine, semantic memory, knowledge graph, CLI, Streamlit UI, exporter, tests, CI, and Docker support.

These are **documented intentions**. Verify every one of them against the repository.

---

# 3. Your First Mission: Understand the Repository

Before making any code changes, inspect the repository thoroughly.

Start by examining:

```text
README.md
pyproject.toml
.gitignore
.env.example
Dockerfile
run.bat
run.ps1
.github/
docs/
scripts/
src/
tests/
```

Then recursively inspect the implementation under:

```text
src/codememory/
```

and the tests under:

```text
tests/
```

Do not merely list files.

For every major subsystem, understand:

1. What files exist?
2. What classes/functions exist?
3. What responsibilities do they have?
4. Who calls them?
5. What data enters the subsystem?
6. What data leaves it?
7. What interfaces/contracts exist?
8. What dependencies does it have?
9. Which parts are actually implemented?
10. Which parts are placeholders, incomplete, dead code, or misleadingly documented?

---

# 4. Build an Actual Architecture Map

Construct an architecture map based on the real code.

Trace the important execution paths.

At minimum, understand:

### Application startup

```text
CLI / Streamlit
      ↓
Application initialization
      ↓
Configuration
      ↓
Core services
      ↓
Repositories / storage
```

### Data ingestion

```text
JSON / CSV / JSONL / LeetCode
      ↓
Parser
      ↓
Normalizer
      ↓
Mapper
      ↓
Domain Models
      ↓
Repository
      ↓
Storage
```

### Analytics

```text
Stored data
    ↓
Analytics services
    ↓
Metrics
    ↓
Insights / Patterns
    ↓
UI
```

### Memory

```text
Historical records
      ↓
Memory document generation
      ↓
Embeddings
      ↓
Index
      ↓
Retriever
      ↓
Relevant memories
```

### Ask CodeMemory

```text
User question
      ↓
Retriever
      ↓
Relevant memories
      ↓
Context builder
      ↓
AI provider
      ↓
Answer
```

### Revision

```text
Historical attempts
      ↓
Difficulty / failures / recency / weaknesses
      ↓
Priority calculation
      ↓
Revision queue
```

### Knowledge graph

Understand exactly how:

```text
Problems
Attempts
Submissions
Topics
Approaches
Mistakes
Languages
Patterns
```

are represented and connected.

Do not assume the documented diagram exactly matches the implementation.

---

# 5. Understand the Domain Model

Inspect the actual Pydantic/domain models.

Determine exactly how the project represents:

* Problem
* Attempt
* Submission
* SolutionAnalysis
* Difficulty
* SubmissionStatus
* Platform
* Topics
* Mistakes
* Notes
* MemoryDocument
* Any other important entities

Document:

* fields
* types
* optionality
* relationships
* IDs
* hashes
* timestamps
* enums
* validation rules

Pay particular attention to how:

```text
Problem → Attempt → Submission
```

is represented.

Understand whether the conceptual model in the README is actually enforced by the code.

---

# 6. Audit Storage Carefully

This is a high-priority area.

Inspect:

```text
src/codememory/storage/
```

including:

```text
base.py
composite_repository.py
duckdb_repository.py
fs_repository.py
parquet_repository.py
```

Determine:

* What interface/base repository defines
* What methods each implementation exposes
* Whether implementations satisfy the interface
* How transactions work
* How atomicity is handled
* How errors are handled
* How data is synchronized between storage layers
* How IDs/deduplication work
* How empty datasets behave
* How initialization works
* Whether there are hidden assumptions between repositories

Pay special attention to any health-check functionality.

There was previously a reported issue where a health check expected:

```python
DuckDBStorage.query()
```

but the implementation did not expose that method.

**Do not assume this bug still exists.**

Run the current tests and inspect the current implementation to determine the present state.

If the issue still exists, determine the correct architectural fix rather than blindly adding a method just to satisfy one test.

---

# 7. Audit the AI System

Inspect:

```text
src/codememory/ai/
```

including:

```text
analyzer.py
base.py
context_builder.py
evolution_service.py
fallback_provider.py
memory_service.py
models.py
prompts.py
providers/
```

Determine:

* How AI providers are abstracted
* What the provider interface looks like
* How OpenAI is called
* What happens when no API key exists
* How heuristic fallback works
* What information is sent to the AI
* How code submissions are analyzed
* How solution evolution is analyzed
* How AI outputs are validated
* Whether AI outputs are persisted
* How caching/versioning works
* Whether repeated requests trigger duplicate AI calls
* How errors/timeouts are handled
* Whether secrets are handled safely

Inspect whether the AI actually analyzes the **user's historical data**, rather than simply behaving like a generic chatbot.

---

# 8. Audit the Memory / RAG System

Inspect:

```text
src/codememory/memory/
```

including:

```text
embeddings.py
index.py
models.py
pipeline.py
retriever.py
service.py
```

Understand the complete lifecycle:

```text
Source record
   ↓
MemoryDocument
   ↓
Content hash
   ↓
Embedding
   ↓
Vector index
   ↓
Retrieval
```

Determine:

* What gets embedded?
* Which records become memory documents?
* How provenance is preserved
* How content hashes are calculated
* How incremental indexing works
* How stale embeddings are detected
* How rebuilding differs from incremental indexing
* Which embedding model is used
* Where embeddings are stored
* How similarity is calculated
* How keyword search works
* How structured filters are combined with semantic similarity
* How ranking works
* What happens when there are no embeddings
* What happens when datasets are empty
* What happens when embedding generation fails

The documented architecture describes a hybrid retrieval system using semantic similarity, keyword matching, and structured criteria.

Verify whether the actual implementation behaves this way.

---

# 9. Audit Search

Inspect:

```text
src/codememory/search/
```

Determine the difference between:

* structured search
* text search
* semantic search
* hybrid search

Trace a real search request from UI/CLI to the final result.

Look for:

* ranking issues
* duplicated results
* poor filtering
* missing metadata
* inefficient scans
* unnecessary recomputation
* inconsistent result formats

---

# 10. Audit Analytics, Patterns and Revision

Inspect:

```text
analytics/
patterns/
revision/
```

Understand what is actually calculated.

Identify:

### Analytics

* total problems
* attempts
* acceptance rates
* difficulty distribution
* topic distribution
* solving velocity
* struggle problems
* any additional metrics

### Patterns

Determine whether the system can actually infer things such as:

* recurring algorithms
* recurring mistakes
* complexity patterns
* weak topics
* language preferences
* problem-solving behavior

### Revision

Inspect the priority formula and implementation.

Determine:

* inputs
* weights
* scoring
* sorting
* exclusions
* recency handling
* weakness handling
* difficulty handling

Verify that the UI's explanation matches the actual calculation.

---

# 11. Audit LeetCode Integration

Inspect:

```text
src/codememory/connectors/leetcode/
```

including:

```text
capabilities.py
client.py
importer.py
leetcode_connector.py
mapper.py
models.py
parser.py
sync.py
```

Determine exactly what is currently supported.

Pay particular attention to the distinction between:

* manual import
* dataset import
* account connection
* synchronization
* incremental synchronization

Verify that the project does NOT make unsupported claims about private LeetCode access.

The documented security direction is:

```text
NO passwords
NO cookies
NO scraping
NO unofficial APIs
```

with a manual import fallback.

Verify that the current implementation follows this constraint.

---

# 12. Audit the Streamlit Application

Inspect:

```text
src/codememory/app/
```

including all pages/views.

Determine which pages are:

* fully functional
* partially functional
* placeholder
* broken
* visually incomplete
* disconnected from backend functionality

Inspect at least:

```text
dashboard
problems
problem detail
solution
analytics
patterns
revision
search
graph
ask CodeMemory
import
export
settings
```

For every page, determine:

1. What does the user see?
2. What service does it call?
3. Is the backend integration real?
4. Is the displayed data correct?
5. Are loading/error/empty states handled?
6. Are there hardcoded values?
7. Are there UI inconsistencies?
8. Are there performance problems?
9. Are there broken interactions?
10. Is the feature actually usable end-to-end?

---

# 13. Audit the CLI

Inspect:

```text
src/codememory/cli/
```

Determine all supported commands.

Compare CLI functionality against README documentation.

Check:

* command registration
* argument validation
* error handling
* output formatting
* missing commands
* broken commands
* inconsistent behavior between CLI and UI

---

# 14. Audit Tests

Run the complete test suite.

Start with:

```bash
pytest -v
```

Then run coverage:

```bash
pytest --cov=codememory
```

Do not just report the number of passing tests.

Analyze:

* failing tests
* skipped tests
* weak tests
* missing edge cases
* integration gaps
* tests that only test mocks rather than real behavior
* areas with low coverage
* important code paths without tests

Map tests to architecture.

For example:

```text
Domain → tests
Storage → tests
Import → tests
LeetCode → tests
AI → tests
Memory → tests
Search → tests
Graph → tests
Revision → tests
UI → tests
```

Identify areas that appear implemented but are insufficiently tested.

---

# 15. Run the Project, If Practical

If the environment allows it, actually run the application.

Try the documented commands and relevant entry points.

For example:

```bash
codememory --help
codememory ui
codememory seed
codememory memory index
codememory memory search "sliding window"
codememory patterns
codememory graph
```

Do not execute commands blindly if dependencies/environment configuration are missing.

Instead document:

* what works
* what fails
* exact error
* likely cause
* severity

If the Streamlit application can be launched, inspect the major user flows.

---

# 16. Compare Documentation vs Reality

Create a dedicated section:

## Documentation vs Implementation

For every major documented capability, classify it as:

```text
IMPLEMENTED
PARTIALLY IMPLEMENTED
BROKEN
NOT IMPLEMENTED
DOCUMENTATION ONLY
UNCLEAR
```

Examples:

```text
AI analysis                 → ?
Semantic memory             → ?
Hybrid search               → ?
Knowledge graph             → ?
Revision engine             → ?
LeetCode import             → ?
LeetCode sync               → ?
OpenAI provider             → ?
Heuristic fallback          → ?
Export                      → ?
CLI                         → ?
Streamlit UI                → ?
Docker                      → ?
CI                          → ?
```

Do not mark something implemented merely because a file exists.

Trace actual execution.

---

# 17. Find Technical Debt

Look for:

* TODOs
* FIXMEs
* commented-out code
* dead code
* duplicated logic
* overly large functions
* circular dependencies
* unnecessary coupling
* inconsistent naming
* inconsistent interfaces
* type issues
* broad exception handling
* silent failures
* hardcoded configuration
* magic numbers
* repeated database logic
* repeated parsing logic
* duplicated UI logic
* unnecessary dependencies
* stale documentation
* unused imports
* unused classes/functions
* unreachable code

Also identify architectural inconsistencies.

Do not refactor everything simply because it could be cleaner.

Prioritize improvements based on actual impact.

---

# 18. Security Audit

Perform a lightweight security review.

Check:

* API key handling
* `.env` handling
* secret exposure
* filesystem access
* uploaded file handling
* arbitrary code execution risks
* unsafe subprocess usage
* SQL construction
* path traversal
* deserialization risks
* external API usage
* logging of sensitive data
* user source-code privacy
* AI provider data exposure

CodeMemory is intended to be local-first and privacy-conscious, so explicitly evaluate whether implementation matches that goal.

---

# 19. Performance Audit

Identify potential performance bottlenecks.

Pay attention to:

* loading entire Parquet datasets unnecessarily
* repeated DuckDB queries
* repeated embedding generation
* unnecessary rebuilding of indexes
* Streamlit reruns
* expensive graph construction
* repeated AI calls
* missing caching
* large historical datasets
* inefficient Python loops where vectorized/database operations would be more appropriate

Do not optimize prematurely.

Identify measurable or plausible bottlenecks and explain why they matter.

---

# 20. Developer Experience Audit

Evaluate how easy it is for a new contributor to join the project.

Check:

* setup instructions
* dependency installation
* environment configuration
* seed data
* test commands
* development workflow
* Docker setup
* CI
* branch/PR friendliness
* documentation
* code organization

Identify anything that would make collaboration difficult.

---

# 21. Identify the Current Project State

After the audit, produce a clear capability matrix.

Use this format:

| Area      | Current State | Evidence | Issues | Priority |
| --------- | ------------- | -------- | ------ | -------- |
| Domain    |               |          |        |          |
| Storage   |               |          |        |          |
| Import    |               |          |        |          |
| LeetCode  |               |          |        |          |
| Analytics |               |          |        |          |
| Patterns  |               |          |        |          |
| Revision  |               |          |        |          |
| Search    |               |          |        |          |
| Memory    |               |          |        |          |
| AI        |               |          |        |          |
| Graph     |               |          |        |          |
| CLI       |               |          |        |          |
| Streamlit |               |          |        |          |
| Export    |               |          |        |          |
| Tests     |               |          |        |          |
| CI        |               |          |        |          |
| Docker    |               |          |        |          |

Use evidence from actual files/functions/tests wherever possible.

---

# 22. Identify What Is Actually Pending

Create:

## Critical / Blocking

Things that should be fixed before meaningful feature development.

## High Priority

Important issues that affect reliability, architecture, or core functionality.

## Medium Priority

Useful improvements but not blockers.

## Low Priority / Future

Nice-to-have improvements.

Do not simply copy the README roadmap.

Determine what is genuinely pending based on the repository.

---

# 23. Suggest New Features Carefully

After understanding the current system, suggest features that naturally strengthen the core product.

Potential areas to investigate include:

* better personal learning insights
* stronger solution evolution analysis
* better mistake detection
* improved revision intelligence
* richer semantic retrieval
* improved Ask CodeMemory
* better graph exploration
* IDE integration
* automated coding-session capture
* richer problem similarity
* learning streak/progress intelligence
* personalized study plans
* improved explainability of AI insights

However:

**Do not add features just because they sound impressive.**

Every suggestion must answer:

1. What user problem does it solve?
2. Why does it fit CodeMemory?
3. What existing architecture can support it?
4. What new architecture/data would be required?
5. What is the implementation complexity?
6. What could go wrong?

---

# 24. Collaboration Readiness

Because another developer/agent is joining an existing project, evaluate how safely new contributors can work on it.

Identify logical workstreams such as:

```text
Workstream A — Core / Storage
Workstream B — AI / Memory
Workstream C — UI / UX
Workstream D — Integrations
Workstream E — Testing / Quality
```

Recommend boundaries that minimize conflicts.

Identify files/modules that are likely to become merge-conflict hotspots.

Recommend which areas can be developed independently.

---

# 25. Do NOT Make Changes Yet

Unless you discover an extremely obvious safety issue that must be fixed immediately, **do not modify the repository during this initial audit.**

The output of this task should be an investigation/report.

We will decide what to implement after reviewing your findings.

Do not:

* rewrite architecture
* upgrade dependencies randomly
* replace frameworks
* rewrite working modules
* add arbitrary abstractions
* delete existing code
* "clean up" unrelated files
* fix tests by weakening assertions
* change CI just to make it green
* add methods purely to satisfy one test without understanding the interface
* introduce new technologies without justification

---

# 26. Final Deliverable

At the end, produce a comprehensive but practical report with this exact structure:

# CodeMemory Repository Audit

## 1. Executive Summary

Explain CodeMemory in your own words based on the actual implementation.

## 2. What Has Been Built

List the major implemented capabilities.

## 3. Architecture

Show the actual architecture and important dependency/data flows.

## 4. Repository Structure

Explain important directories/modules and their responsibilities.

## 5. Data Model

Explain the core entities and relationships.

## 6. End-to-End Data Flow

Trace at least one real example from ingestion → storage → analytics/memory → AI/UI.

## 7. Current Feature Status

Provide the capability matrix.

## 8. What Works

List verified working functionality.

## 9. What Is Broken

List verified failures with evidence and reproduction details.

## 10. What Is Incomplete

List partially implemented or disconnected features.

## 11. Documentation vs Reality

Identify stale, incorrect, or overly optimistic documentation.

## 12. Tests & CI

Report actual current test status, coverage if available, and important missing tests.

## 13. Technical Debt

List meaningful technical debt.

## 14. Security Findings

List security/privacy concerns and severity.

## 15. Performance Findings

List meaningful performance concerns.

## 16. UX / Product Findings

Identify usability problems or incomplete user flows.

## 17. Collaboration Risks

Identify modules/files/workflows that may cause contributor conflicts.

## 18. Recommended Work Breakdown

Suggest logical independent workstreams for contributors.

## 19. Recommended Next Steps

Give a prioritized sequence of work.

## 20. Future Improvements

Suggest worthwhile improvements/features after the current implementation is stabilized.

## 21. Questions / Unknowns

Explicitly list anything you could not determine from the repository.

---

# 27. Evidence Rules

Be precise.

Whenever possible, reference:

```text
file path
class/function
test name
configuration
```

For example:

```text
src/codememory/storage/duckdb_repository.py
DuckDBRepository.health_check()

tests/test_phase8_hardening.py::test_health_check_all_ok
```

Do not say:

> "The storage system seems broken."

Instead say:

> "`X` calls `Y`, but `Y` does not implement `Z`, which causes test `A` to fail."

Separate:

```text
Verified fact
Inference
Recommendation
```

Do not present an inference as a fact.

---

# 28. Most Important Rule

Think like a senior engineer taking ownership of an unfamiliar production codebase.

Your goal is to answer:

> **"If I had never seen CodeMemory before and needed to start contributing tomorrow, what would I need to know?"**

Understand the system before changing it.

Do not optimize for the number of issues found.

Optimize for an accurate understanding of:

```text
WHAT EXISTS
WHAT WORKS
WHAT DOESN'T
WHAT IS MISSING
WHY IT MATTERS
WHAT SHOULD HAPPEN NEXT
```

Only after this audit is complete should we decide which implementation tasks to give you.
