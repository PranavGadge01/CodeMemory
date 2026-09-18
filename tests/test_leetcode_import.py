"""End-to-end integration test for LeetCode dataset importing, idempotency, and knowledge file generation."""

from pathlib import Path
import pytest

from codememory.connectors.leetcode.importer import LeetCodeImporter
from codememory.connectors.leetcode.leetcode_connector import LeetCodeConnector
from codememory.domain.enums import SubmissionStatus
from codememory.storage.composite_repository import CompositeStorage

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "leetcode"


def test_leetcode_import_and_idempotency(tmp_path: Path):
    """Test importing LeetCode dataset twice to verify zero duplicates on second run."""
    db_path = tmp_path / "test_leetcode.duckdb"
    knowledge_dir = tmp_path / "knowledge"
    storage = CompositeStorage(base_dir=tmp_path, knowledge_dir=knowledge_dir, db_path=db_path)

    importer = LeetCodeImporter(storage=storage)
    json_path = FIXTURES_DIR / "sample_leetcode.json"

    # First import
    summary1 = importer.import_file(json_path)
    assert summary1.valid_count == 6
    assert summary1.imported_count == 6
    assert summary1.duplicate_count == 0
    assert len(summary1.imported_problems) == 3

    # Verify problem detail in storage
    two_sum = storage.get_by_slug("two-sum")
    assert two_sum is not None
    assert two_sum.title == "Two Sum"
    assert two_sum.difficulty == "Easy"

    # Check that attempts exist
    attempts = two_sum.attempts
    assert len(attempts) >= 1

    # Flatten all submissions across attempts
    all_subs = [sub for att in attempts for sub in att.submissions]
    assert len(all_subs) == 3

    # Verify statuses: WA, TLE, Accepted
    statuses = [sub.status for sub in all_subs]
    assert SubmissionStatus.WRONG_ANSWER in statuses
    assert SubmissionStatus.TIME_LIMIT_EXCEEDED in statuses
    assert SubmissionStatus.ACCEPTED in statuses

    # Second import of exact same dataset (Idempotency Check)
    summary2 = importer.import_file(json_path)
    assert summary2.imported_count == 0
    assert summary2.duplicate_count == 6

    # Verify storage contents remain intact without duplicates
    two_sum_after = storage.get_by_slug("two-sum")
    all_subs_after = [sub for att in two_sum_after.attempts for sub in att.submissions]
    assert len(all_subs_after) == 3


def test_leetcode_incremental_import(tmp_path: Path):
    """Test incremental importing of CSV dataset after JSON dataset."""
    db_path = tmp_path / "test_leetcode_inc.duckdb"
    knowledge_dir = tmp_path / "knowledge"
    storage = CompositeStorage(base_dir=tmp_path, knowledge_dir=knowledge_dir, db_path=db_path)

    connector = LeetCodeConnector(storage=storage)

    json_path = FIXTURES_DIR / "sample_leetcode.json"
    csv_path = FIXTURES_DIR / "sample_leetcode.csv"

    # Day 1: JSON import (6 submissions, 3 problems)
    s1 = connector.import_dataset(json_path)
    assert s1.imported_count == 6

    # Day 2: CSV import (2 submissions, 2 new problems)
    s2 = connector.import_dataset(csv_path)
    assert s2.imported_count == 2

    # Verify total problem count in storage
    all_probs = storage.list_all()
    assert len(all_probs) == 5

    # Check knowledge files generated
    assert (knowledge_dir / "two-sum" / "problem.md").exists()
    assert (knowledge_dir / "valid-parentheses" / "problem.md").exists()
