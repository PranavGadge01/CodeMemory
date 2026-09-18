"""Unit tests for import schema validation and fallback parsers."""

from datetime import datetime, timezone
import pytest

from codememory.domain.enums import DifficultyLevel, SubmissionStatus
from codememory.domain.import_schema import (
    NormalizedSubmissionRecord,
    parse_memory,
    parse_runtime,
    parse_timestamp,
    parse_topics,
)


def test_parse_runtime():
    assert parse_runtime(45.5) == 45.5
    assert parse_runtime("45.5 ms") == 45.5
    assert parse_runtime("0.5 s") == 500.0
    assert parse_runtime(None) is None
    assert parse_runtime("") is None


def test_parse_memory():
    assert parse_memory(16.4) == 16.4
    assert parse_memory("16.4 MB") == 16.4
    assert parse_memory("2048 KB") == 2.0
    assert parse_memory(None) is None


def test_parse_timestamp():
    dt_iso = parse_timestamp("2026-09-06T12:00:00Z")
    assert isinstance(dt_iso, datetime)
    assert dt_iso.year == 2026

    dt_fmt = parse_timestamp("2026-09-06 14:30:00")
    assert dt_fmt.hour == 14

    dt_epoch = parse_timestamp(1700000000)
    assert isinstance(dt_epoch, datetime)


def test_parse_topics():
    assert parse_topics("Array, Hash Table, Dynamic Programming") == ["Array", "Hash Table", "Dynamic Programming"]
    assert parse_topics(["Tree", "BFS"]) == ["Tree", "BFS"]
    assert parse_topics(None) == []


def test_normalized_record_validation():
    data = {
        "title": " 3Sum ",
        "difficulty": "med",
        "topics": "Array, Two Pointers",
        "language": "PYTHON3",
        "code": "def threeSum(nums): pass",
        "status": "Accepted",
        "runtime": "120 ms",
        "memory": "18.5 MB",
        "timestamp": "2026-09-06T10:00:00Z",
    }

    rec = NormalizedSubmissionRecord.model_validate(data)
    assert rec.title == "3Sum"
    assert rec.problem_id == "3sum"
    assert rec.difficulty == DifficultyLevel.MEDIUM
    assert rec.status == SubmissionStatus.ACCEPTED
    assert rec.runtime_ms == 120.0
    assert rec.memory_mb == 18.5
    assert rec.topics == ["Array", "Two Pointers"]
    assert len(rec.submission_hash) == 64
