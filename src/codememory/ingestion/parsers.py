"""File format parsers for JSON, CSV, and JSONL ingestion."""

import csv
import json
from pathlib import Path
from typing import Any

from codememory.domain.exceptions import ImportError


def parse_json_file(file_path: Path) -> list[dict[str, Any]]:
    """Parse JSON file containing a single object or list of objects."""
    try:
        content = file_path.read_text(encoding="utf-8").strip()
        if not content:
            return []
        data = json.loads(content)
        if isinstance(data, dict):
            # Check if wrapped under a key like "submissions" or "data"
            if "submissions" in data and isinstance(data["submissions"], list):
                return data["submissions"]
            if "data" in data and isinstance(data["data"], list):
                return data["data"]
            return [data]
        if isinstance(data, list):
            return list(data)
        return []
    except Exception as e:
        raise ImportError(f"Failed to parse JSON file '{file_path}': {e}") from e


def parse_jsonl_file(file_path: Path) -> list[dict[str, Any]]:
    """Parse JSON Lines file (one JSON object per line)."""
    records: list[dict[str, Any]] = []
    try:
        lines = file_path.read_text(encoding="utf-8").splitlines()
        for idx, line in enumerate(lines, 1):
            line_str = line.strip()
            if not line_str:
                continue
            try:
                obj = json.loads(line_str)
                if isinstance(obj, dict):
                    records.append(obj)
            except json.JSONDecodeError as e:
                # Log or skip malformed line gracefully
                continue
        return records
    except Exception as e:
        raise ImportError(f"Failed to parse JSONL file '{file_path}': {e}") from e


def parse_csv_file(file_path: Path) -> list[dict[str, Any]]:
    """Parse CSV file into list of row dictionaries."""
    records: list[dict[str, Any]] = []
    try:
        content = file_path.read_text(encoding="utf-8")
        reader = csv.DictReader(content.splitlines())
        for row in reader:
            if any(v.strip() for v in row.values() if v):
                records.append(dict(row))
        return records
    except Exception as e:
        raise ImportError(f"Failed to parse CSV file '{file_path}': {e}") from e


def parse_file(file_path: str | Path) -> list[dict[str, Any]]:
    """Auto-detect format and parse file into list of dictionaries."""
    path = Path(file_path)
    if not path.exists():
        raise ImportError(f"File not found: '{file_path}'")

    ext = path.suffix.lower()
    if ext == ".json":
        return parse_json_file(path)
    elif ext in (".jsonl", ".ndjson"):
        return parse_jsonl_file(path)
    elif ext == ".csv":
        return parse_csv_file(path)
    else:
        # Fallback: try JSON then JSONL then CSV
        try:
            return parse_json_file(path)
        except Exception:
            try:
                return parse_jsonl_file(path)
            except Exception:
                return parse_csv_file(path)
