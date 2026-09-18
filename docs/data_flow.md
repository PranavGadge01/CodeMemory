# Data Flow

## Data Ingestion Sequence

```
User File (JSON / CSV / JSONL)
        │
        ▼
   parse_file() -> Raw Dicts
        │
        ▼
ImportService.validate_import()
        │
        ▼
NormalizedSubmissionRecord (Schema validation & unit conversions)
        │
        ▼
Idempotency Check (SHA-256 Hash / Submission ID lookup in DuckDB)
   ├── Match Found ──> Skip (Increment Duplicate Counter)
   └── No Match    ──> Convert to Domain Problem/Attempt/Submission
                             │
                             ▼
                    CompositeStorage.save()
                   ┌─────────┴─────────┐
                   ▼                   ▼
           DuckDB & Parquet   Filesystem Knowledge Base
           (Relational/Parquet) (knowledge/<slug>/problem.md)
```

## Knowledge Base Generation Flow

```
CodeMemoryService.export_knowledge()
        │
        ▼
KnowledgeExporter
        │
        ▼
Iterate over Problems:
 ├── Write knowledge/<slug>/problem.md
 ├── Write knowledge/<slug>/attempts.md
 ├── Write knowledge/<slug>/solution.<ext> (Latest Accepted Code)
 └── Write knowledge/<slug>/metadata.json
```
