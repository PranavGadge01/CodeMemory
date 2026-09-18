"""LeetCode dataset parser supporting JSON and CSV formats."""

import csv
import json
from pathlib import Path
from typing import Any, List, Union

from pydantic import ValidationError

from codememory.connectors.leetcode.models import LeetCodeSubmissionRaw
from codememory.domain.exceptions import ImportError


class LeetCodeParser:
    """Parser for reading and validating LeetCode JSON and CSV exports."""

    @staticmethod
    def _normalize_dict_keys(record: dict[str, Any]) -> dict[str, Any]:
        """Map common LeetCode export column names and key variations to model field names."""
        normalized: dict[str, Any] = {}
        
        # Key aliases mapping
        field_mappings = {
            "title": ["title", "Problem Title", "problem_title", "title_slug", "Question Title"],
            "title_slug": ["title_slug", "slug", "problem_slug", "Question Slug"],
            "id": ["id", "submission_id", "Submission ID", "question_id"],
            "difficulty": ["difficulty", "Difficulty", "Level"],
            "language": ["language", "lang", "Language"],
            "code": ["code", "source_code", "Code", "Source Code", "submission_code"],
            "status": ["status", "status_display", "Status", "Result"],
            "runtime": ["runtime", "Runtime", "Execution Time"],
            "memory": ["memory", "Memory", "Memory Usage"],
            "timestamp": ["timestamp", "Timestamp", "Date", "submitted_at", "created_at"],
            "url": ["url", "URL", "link", "Problem URL"],
            "topics": ["topics", "Topics", "tags", "Tags", "topic_tags"],
            "notes": ["notes", "Notes", "reasoning", "Reasoning", "Notes/Reasoning"],
        }

        for field_name, aliases in field_mappings.items():
            for alias in aliases:
                if alias in record and record[alias] is not None:
                    val = record[alias]
                    # Handle string topics split by comma if needed
                    if field_name == "topics" and isinstance(val, str):
                        val = [t.strip() for t in val.split(",") if t.strip()]
                    normalized[field_name] = val
                    break

        # Copy any remaining unmapped keys
        for k, v in record.items():
            if k not in normalized and isinstance(k, str):
                normalized[k] = v

        return normalized

    @classmethod
    def parse_records(cls, raw_items: list[dict[str, Any]]) -> tuple[list[LeetCodeSubmissionRaw], list[str]]:
        """Validate raw dictionary records into LeetCodeSubmissionRaw objects."""
        parsed_records: list[LeetCodeSubmissionRaw] = []
        errors: list[str] = []

        for idx, item in enumerate(raw_items, 1):
            if not isinstance(item, dict):
                errors.append(f"Record #{idx}: Item is not a dictionary.")
                continue

            try:
                norm_dict = cls._normalize_dict_keys(item)
                if not norm_dict.get("title"):
                    errors.append(f"Record #{idx}: Missing problem title.")
                    continue
                if not norm_dict.get("language"):
                    errors.append(f"Record #{idx}: Missing programming language.")
                    continue
                if not norm_dict.get("status"):
                    errors.append(f"Record #{idx}: Missing submission status.")
                    continue

                raw_model = LeetCodeSubmissionRaw.model_validate(norm_dict)
                parsed_records.append(raw_model)
            except ValidationError as ve:
                errors.append(f"Record #{idx} ({item.get('title', 'Unknown')}): Validation failed: {ve}")
            except Exception as e:
                errors.append(f"Record #{idx}: Parsing error: {e}")

        return parsed_records, errors

    @classmethod
    def parse_json(cls, file_or_content: Union[str, Path]) -> tuple[list[LeetCodeSubmissionRaw], list[str]]:
        """Parse LeetCode JSON file or JSON string."""
        path = Path(file_or_content) if isinstance(file_or_content, (str, Path)) and Path(file_or_content).exists() else None
        
        try:
            if path:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = json.loads(str(file_or_content))
        except Exception as e:
            raise ImportError(f"Failed to decode JSON data: {e}")

        if isinstance(data, dict):
            # If wrapped in a root object like {"submissions": [...]} or {"data": [...]}
            data = data.get("submissions") or data.get("data") or data.get("records") or [data]

        if not isinstance(data, list):
            raise ImportError("LeetCode JSON content must be an array of submission objects or a dict containing a submissions list.")

        return cls.parse_records(data)

    @classmethod
    def parse_csv(cls, file_or_content: Union[str, Path]) -> tuple[list[LeetCodeSubmissionRaw], list[str]]:
        """Parse LeetCode CSV file or CSV string."""
        path = Path(file_or_content) if isinstance(file_or_content, (str, Path)) and Path(file_or_content).exists() else None

        raw_items: list[dict[str, Any]] = []
        try:
            if path:
                with open(path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    raw_items = list(reader)
            else:
                reader = csv.DictReader(str(file_or_content).splitlines())
                raw_items = list(reader)
        except Exception as e:
            raise ImportError(f"Failed to read CSV data: {e}")

        return cls.parse_records(raw_items)

    @classmethod
    def parse_file(cls, file_path: Union[str, Path]) -> tuple[list[LeetCodeSubmissionRaw], list[str]]:
        """Parse file based on extension (.json, .csv)."""
        path = Path(file_path)
        if not path.exists():
            raise ImportError(f"File not found: '{file_path}'")

        ext = path.suffix.lower()
        if ext == ".json":
            return cls.parse_json(path)
        elif ext == ".csv":
            return cls.parse_csv(path)
        else:
            raise ImportError(f"Unsupported file extension '{ext}'. Only .json and .csv are supported.")
