# CodeMemory Architecture Documentation

CodeMemory is built around a **decoupled, multi-tier composite storage engine** and layered application service architecture.

```
UI (Streamlit Studio) / CLI (Rich Terminal)
               ↓
    CodeMemory Core Services
  (Search, Revision, Analytics, AI Analysis, Knowledge Graph, Importer, Exporter)
               ↓
        Domain Models (Pydantic v2)
               ↓
     Storage Repository Interface
               ↓
 ┌────────────────────────────────────────────────────────┐
 │ Composite Storage Coordinator                           │
 ├───────────────────┬───────────────────┬────────────────┤
 │ Filesystem        │ Parquet Columnar  │ DuckDB Engine  │
 │ (Markdown KB)     │ (Polars Datasets) │ (Relational)   │
 └───────────────────┴───────────────────┴────────────────┘
```

## Key Architectural Decisions

1. **Decoupled Business Logic**: Streamlit UI components and CLI commands never issue raw SQL or access storage internals directly; all operations execute through `CodeMemoryService`.
2. **Multi-Tier Composite Storage**:
   - **Filesystem (Markdown)**: Stores readable, Git-friendly problem notes (`problem.md`, `attempts.md`, `notes.md`, source code files).
   - **Parquet Columnar Engine**: Powered by Polars for fast columnar analytical scans over millions of historical submission events.
   - **DuckDB Query Engine**: High-performance SQL query layer powering complex joins, stats aggregation, and indexed lookups without requiring a standalone database server.
3. **Idempotency & Hash Matching**: Every submission is assigned a deterministic SHA-256 hash computed from problem ID, code content, and timestamp. Duplicate submissions are automatically detected and skipped during imports.
4. **Offline Heuristic AI Provider**: AI solution analysis operates behind an abstract `BaseAIProvider` interface. When no external LLM API key is present, CodeMemory uses a local rule-based AST/regex provider (`HeuristicAIProvider`) to infer algorithm designs, time/space complexities, and failure modes.
