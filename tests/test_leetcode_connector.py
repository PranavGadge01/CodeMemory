"""Unit tests for LeetCode connector components (parser, mapper, client, connector)."""

import socket

from pathlib import Path
import pytest

from codememory.connectors.leetcode.client import LeetCodeClient
from codememory.connectors.leetcode.leetcode_connector import LeetCodeConnector
from codememory.connectors.leetcode.mapper import LeetCodeMapper
from codememory.connectors.leetcode.models import LeetCodeSubmissionRaw
from codememory.connectors.leetcode.parser import LeetCodeParser
from codememory.domain.enums import SubmissionStatus

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "leetcode"

# Bounded so an offline machine fails the probe quickly instead of hanging.
_LIVE_PROBE_TIMEOUT = 3.0


def _require_leetcode_reachable() -> None:
    """Skip unless leetcode.com can be reached within a short bound.

    Lives inside the test body rather than in a ``skipif`` condition on purpose:
    pytest evaluates ``skipif`` expressions at collection time even for tests that
    are deselected by a marker filter, so a probe placed there would make every
    ordinary test run touch the network. Body-level code runs only when the test
    is actually selected, i.e. only under ``pytest -m live``.
    """
    try:
        with socket.create_connection(("leetcode.com", 443), timeout=_LIVE_PROBE_TIMEOUT):
            pass
    except OSError as exc:
        pytest.skip(f"leetcode.com unreachable ({exc}); live integration test skipped")



def test_leetcode_parser_json():
    """Test parsing sample LeetCode JSON export."""
    json_path = FIXTURES_DIR / "sample_leetcode.json"
    records, errors = LeetCodeParser.parse_file(json_path)

    assert len(errors) == 0
    assert len(records) == 6
    assert records[0].title == "Two Sum"
    assert records[0].status == "Wrong Answer"
    assert records[2].status == "Accepted"


def test_leetcode_parser_csv():
    """Test parsing sample LeetCode CSV export."""
    csv_path = FIXTURES_DIR / "sample_leetcode.csv"
    records, errors = LeetCodeParser.parse_file(csv_path)

    assert len(errors) == 0
    assert len(records) == 2
    assert records[0].title == "Valid Parentheses"
    assert records[0].language == "python3"
    assert records[1].status == "Time Limit Exceeded"


def test_leetcode_mapper_status_normalization():
    """Test mapping raw status strings to SubmissionStatus enums."""
    assert LeetCodeMapper.normalize_status("Accepted") == SubmissionStatus.ACCEPTED
    assert LeetCodeMapper.normalize_status("ac") == SubmissionStatus.ACCEPTED
    assert LeetCodeMapper.normalize_status("10") == SubmissionStatus.ACCEPTED
    assert LeetCodeMapper.normalize_status("Wrong Answer") == SubmissionStatus.WRONG_ANSWER
    assert LeetCodeMapper.normalize_status("Time Limit Exceeded") == SubmissionStatus.TIME_LIMIT_EXCEEDED
    assert LeetCodeMapper.normalize_status("Memory Limit Exceeded") == SubmissionStatus.MEMORY_LIMIT_EXCEEDED
    assert LeetCodeMapper.normalize_status("Runtime Error") == SubmissionStatus.RUNTIME_ERROR
    assert LeetCodeMapper.normalize_status("Compile Error") == SubmissionStatus.COMPILE_ERROR
    assert LeetCodeMapper.normalize_status("Random Status") == SubmissionStatus.UNKNOWN


def test_leetcode_mapper_language_normalization():
    """Test normalizing raw language identifiers."""
    assert LeetCodeMapper.normalize_language("python3") == "Python"
    assert LeetCodeMapper.normalize_language("cpp") == "C++"
    assert LeetCodeMapper.normalize_language("java") == "Java"
    assert LeetCodeMapper.normalize_language("golang") == "Go"
    assert LeetCodeMapper.normalize_language("javascript") == "JavaScript"
    assert LeetCodeMapper.normalize_language("rust") == "Rust"


def test_leetcode_mapper_timestamp_and_hash():
    """Test timestamp parsing and deterministic submission hash generation."""
    raw = LeetCodeSubmissionRaw(
        submission_id="999",
        title="Two Sum",
        title_slug="two-sum",
        difficulty="Easy",
        topics=["Array"],
        language="python3",
        status="Accepted",
        timestamp=1700000000,
        code="print('hello')",
    )

    norm_rec = LeetCodeMapper.to_normalized_record(raw)
    assert norm_rec.title == "Two Sum"
    assert norm_rec.difficulty == "Easy"
    assert norm_rec.language == "Python"
    assert norm_rec.status == SubmissionStatus.ACCEPTED
    assert norm_rec.submission_id == "leetcode_999"
    assert norm_rec.submission_hash is not None
    assert len(norm_rec.submission_hash) == 64


@pytest.mark.live
def test_leetcode_client_live_fallback():
    """Live integration test against the real public LeetCode GraphQL endpoint.

    Deliberately NOT part of the default selection: it verifies the actual
    transport contract (an unknown user yields no submissions; a well-known slug
    resolves) against leetcode.com, which no CI runner should depend on. Marked
    ``live`` so ``-m 'not live'`` (the default in pyproject) skips it.

    Run it intentionally with::

        pytest -m live tests/test_leetcode_connector.py::test_leetcode_client_live_fallback
    """
    _require_leetcode_reachable()

    client = LeetCodeClient()
    submissions = client.fetch_user_submissions("non_existent_user_12345")
    assert isinstance(submissions, list)
    assert len(submissions) == 0

    details = client.fetch_problem_details("two-sum")
    assert details is not None
    assert details.title_slug == "two-sum"
