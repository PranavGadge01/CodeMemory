"""Tests for platform connectors extension point."""

from codememory.connectors.base import RawExternalSubmission
from codememory.connectors.leetcode.leetcode_connector import LeetCodeConnector


def test_connector_normalization():
    connector = LeetCodeConnector()
    raw = RawExternalSubmission(
        external_id="sub-lc-123",
        problem_title="Two Sum",
        problem_slug="two-sum",
        difficulty="Easy",
        topics=["Array", "Hash Table"],
        language="python",
        code="def twoSum(nums, target): pass",
        status="Accepted",
        runtime="45 ms",
        memory="16.4 MB",
        timestamp="2026-09-06T10:00:00Z",
        url="https://leetcode.com/problems/two-sum/",
    )

    norm = connector.normalize_submission(raw)
    assert norm.title == "Two Sum"
    assert norm.difficulty == "Easy"
    assert norm.topics == ["Array", "Hash Table"]
    # Language spelling is canonicalized so that the connector and file-import
    # paths cannot disagree on a submission's language (which would otherwise
    # produce different deduplication hashes for the same submission).
    assert norm.language == "Python"
    assert norm.problem_id == "two-sum"
    assert norm.status == "Accepted"
    assert norm.submission_id == "sub-lc-123"


def test_leetcode_connector_methods():
    connector = LeetCodeConnector()
    subs = connector.fetch_user_submissions("test_user")
    assert isinstance(subs, list)
    assert len(subs) == 0

    details = connector.fetch_problem_details("two-sum")
    assert details is not None
    assert details["title"] == "Two Sum"
    assert details["platform"] == "LeetCode"
