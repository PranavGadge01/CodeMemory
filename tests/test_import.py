"""Unit tests for multi-format data ingestion and idempotency guarantees."""

import json
from pathlib import Path
import pytest

from codememory.core.service import CodeMemoryService


def test_json_import(tmp_path: Path):
    service = CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "data" / "test.duckdb",
    )

    data = [
        {
            "title": "3Sum",
            "difficulty": "Medium",
            "topics": ["Array", "Two Pointers"],
            "url": "https://leetcode.com/problems/3sum/",
            "language": "python",
            "code": "def threeSum(nums): pass",
            "timestamp": "2026-09-06T10:00:00Z",
            "status": "Accepted",
            "runtime": "140 ms",
            "memory": "18.2 MB",
            "submission_id": "sub-101",
        }
    ]

    json_file = tmp_path / "data.json"
    json_file.write_text(json.dumps(data), encoding="utf-8")

    summary = service.import_data(json_file)
    assert summary.total_read == 1
    assert summary.imported_count == 1
    assert summary.duplicate_count == 0

    prob = service.get_problem("3sum")
    assert prob is not None
    assert prob.title == "3Sum"


def test_csv_import(tmp_path: Path):
    service = CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "data" / "test.duckdb",
    )

    csv_content = """title,difficulty,topics,language,code,timestamp,status,runtime,memory,submission_id
Maximum Subarray,Easy,"Array,Dynamic Programming",python,def maxSubArray(nums): pass,2026-09-06 12:00:00,Accepted,50 ms,28.4 MB,sub-202
"""
    csv_file = tmp_path / "data.csv"
    csv_file.write_text(csv_content, encoding="utf-8")

    summary = service.import_data(csv_file)
    assert summary.total_read == 1
    assert summary.imported_count == 1

    prob = service.get_problem("maximum-subarray")
    assert prob is not None
    assert prob.difficulty.value == "Easy"


def test_jsonl_import(tmp_path: Path):
    service = CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "data" / "test.duckdb",
    )

    jsonl_content = """{"title": "Valid Parentheses", "difficulty": "Easy", "language": "python", "code": "def isValid(s): return True", "status": "Accepted", "timestamp": "2026-09-06T14:00:00Z", "submission_id": "sub-301"}
{"title": "Valid Parentheses", "difficulty": "Easy", "language": "python", "code": "def isValid(s): return False", "status": "Wrong Answer", "timestamp": "2026-09-06T13:50:00Z", "submission_id": "sub-300"}
"""
    jsonl_file = tmp_path / "data.jsonl"
    jsonl_file.write_text(jsonl_content, encoding="utf-8")

    summary = service.import_data(jsonl_file)
    assert summary.total_read == 2
    assert summary.imported_count == 2

    prob = service.get_problem("valid-parentheses")
    assert len(prob.attempts) >= 1


def test_idempotency_duplicate_prevention(tmp_path: Path):
    service = CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "data" / "test.duckdb",
    )

    data = [
        {
            "title": "Search Insert Position",
            "difficulty": "Easy",
            "language": "python",
            "code": "def searchInsert(nums, target): pass",
            "timestamp": "2026-09-06T15:00:00Z",
            "status": "Accepted",
            "submission_id": "dup-id-1",
        }
    ]

    json_file = tmp_path / "data.json"
    json_file.write_text(json.dumps(data), encoding="utf-8")

    # First import
    s1 = service.import_data(json_file)
    assert s1.imported_count == 1
    assert s1.duplicate_count == 0

    # Second import (same file)
    s2 = service.import_data(json_file)
    assert s2.imported_count == 0
    assert s2.duplicate_count == 1

    prob = service.get_problem("search-insert-position")
    total_subs = sum(len(a.submissions) for a in prob.attempts)
    assert total_subs == 1


def test_malformed_records(tmp_path: Path):
    service = CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "data" / "test.duckdb",
    )

    data = [
        {"title": "", "code": "pass"},  # valid title fallback
        "not-a-dict-string",  # malformed
    ]

    json_file = tmp_path / "malformed.json"
    json_file.write_text(json.dumps(data), encoding="utf-8")

    summary = service.import_data(json_file)
    assert summary.error_count > 0
