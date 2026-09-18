# CodeMemory Import Specification

CodeMemory supports idempotent bulk imports from **JSON**, **CSV**, and **JSONL** files.

## Ingestion Fields

| Field Name | Type | Required | Description |
|---|---|---|---|
| `title` | string | **Yes** | Problem title |
| `difficulty` | string | No | `Easy`, `Medium`, or `Hard` |
| `topics` | list / string | No | Array of topic tags or comma-separated string |
| `url` | string | No | Problem web link |
| `language` | string | No | `python`, `cpp`, `java`, etc. (default: `python`) |
| `code` | string | No | Source code string |
| `timestamp` | string | No | ISO-8601 or datetime string |
| `status` | string | No | `Accepted`, `Time Limit Exceeded`, `Wrong Answer`, etc. |
| `runtime` | string/float | No | e.g. `"45 ms"` or `45.0` |
| `memory` | string/float | No | e.g. `"16.4 MB"` or `16.4` |
| `submission_id` | string | No | Optional external ID |

## Example Files

### JSON (`data.json`)
```json
[
  {
    "title": "Two Sum",
    "difficulty": "Easy",
    "topics": ["Array", "Hash Table"],
    "code": "def twoSum(nums, target): pass",
    "language": "python",
    "status": "Accepted",
    "runtime": "45 ms",
    "memory": "16.4 MB"
  }
]
```

### CSV (`data.csv`)
```csv
title,difficulty,topics,code,language,status,runtime,memory
Two Sum,Easy,"Array,Hash Table",def twoSum(): pass,python,Accepted,45 ms,16.4 MB
```

### JSONL (`data.jsonl`)
```jsonl
{"title": "Two Sum", "difficulty": "Easy", "topics": ["Array", "Hash Table"], "status": "Accepted"}
```
