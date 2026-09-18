# Storage Strategy & Rationale

CodeMemory employs a hybrid local-first multi-tier storage design. Each storage technology is chosen for a specific strength:

| Storage Layer | Format / Path | Primary Purpose | Why it was chosen |
|---|---|---|---|
| **Human Knowledge Base** | `knowledge/<slug>/` (Markdown & Code) | Version control & human readability | Standard Markdown and raw code files can be inspected in any editor or committed to GitHub. |
| **Columnar Datasets** | `data/parquet/*.parquet` (Parquet) | Historical analytical storage | Parquet provides high compression, schema enforcement, and rapid analytical queries via Polars. |
| **Relational Index** | `data/codememory.duckdb` (DuckDB) | Fast relational querying & SQL search | DuckDB provides zero-server SQL analytics, relational joins, and sub-millisecond lookups. |

## Storage Synchronization

When a user imports data or records a new submission:
1. **DuckDB** receives upsert operations to maintain relational integrity and index submission hashes for idempotency.
2. **FilesystemStorage** writes formatted Markdown (`problem.md`, `attempts.md`, `notes.md`) and raw solution source code files (`solution.py`, `solution.cpp`, etc.).
3. **ParquetStorage** synchronizes columnar `.parquet` datasets using Polars.
