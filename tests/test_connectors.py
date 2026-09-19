"""Tests for platform connectors extension point.

The connector reaches LeetCode only through its ``client`` seam, so every test
here substitutes a stand-in for the transport. Nothing in this module touches
the network: the one test that does talk to leetcode.com lives behind the
``live`` marker in ``tests/test_leetcode_connector.py``, which the default
``-m 'not live'`` selection excludes.
"""

from codememory.connectors.base import RawExternalSubmission
from codememory.connectors.leetcode.leetcode_connector import LeetCodeConnector
from codememory.connectors.leetcode.models import LeetCodeProblemRaw, LeetCodeSubmissionRaw


class _StubClient:
    """Stand-in for ``LeetCodeClient`` returning canned GraphQL payloads.

    Records every call so a test can prove the connector went through the
    transport seam instead of the real endpoint.
    """

    def __init__(self, submissions=None, problem: LeetCodeProblemRaw | None = None) -> None:
        self.submissions = submissions if submissions is not None else []
        self.problem = problem
        self.submission_calls = 0
        self.problem_calls = 0

    def fetch_user_submissions(self, username: str, limit: int = 50):
        self.submission_calls += 1
        return self.submissions

    def fetch_problem_details(self, slug: str):
        self.problem_calls += 1
        return self.problem


def _raw_submission(**overrides) -> LeetCodeSubmissionRaw:
    base = dict(
        id="sub-lc-123",
        submission_id="sub-lc-123",
        title="Two Sum",
        title_slug="two-sum",
        difficulty="Easy",
        topics=["Array", "Hash Table"],
        language="python3",
        status="Accepted",
        runtime="45 ms",
        memory="16.4 MB",
        timestamp=1700007200,
    )
    base.update(overrides)
    return LeetCodeSubmissionRaw(**base)


def _connect(connector: LeetCodeConnector, *, submissions=None, problem=None) -> _StubClient:
    """Attach an offline transport to a connector and give it back for inspection."""
    stub = _StubClient(submissions=submissions, problem=problem)
    connector.client = stub
    return stub


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
    """The connector's read methods work against an empty public-API response.

    A user with no accepted submissions and a problem the public endpoint does
    not resolve is the offline equivalent of what this test used to hit the live
    endpoint for: an empty list, and details synthesised from the slug.
    """
    connector = LeetCodeConnector()
    stub = _connect(connector, submissions=[], problem=None)

    subs = connector.fetch_user_submissions("test_user")
    assert isinstance(subs, list)
    assert len(subs) == 0

    details = connector.fetch_problem_details("two-sum")
    assert details is not None
    assert details["title"] == "Two Sum"
    assert details["platform"] == "LeetCode"
    assert details["slug"] == "two-sum"

    # The transport seam was used exactly once per call — nothing escaped to the
    # real endpoint.
    assert stub.submission_calls == 1
    assert stub.problem_calls == 1


def test_leetcode_connector_maps_a_real_transport_record():
    """A populated response round-trips through the connector unchanged."""
    connector = LeetCodeConnector()
    stub = _connect(connector, submissions=[_raw_submission(), _raw_submission(submission_id="sub-lc-124", title="3Sum", title_slug="3sum", language="cpp")])

    results = connector.fetch_user_submissions("test_user", limit=2)

    assert [r.external_id for r in results] == ["leetcode_sub-lc-123", "leetcode_sub-lc-124"]
    first = connector.normalize_submission(results[0])
    assert first.language == "Python", "language is canonicalised before dedup hashing"
    assert first.problem_id == "two-sum"
    assert first.submission_id == "leetcode_sub-lc-123"
    assert stub.submission_calls == 1, "one request per fetch, never per record"


def test_leetcode_connector_uses_the_supplied_problem_payload():
    """Details from the transport are passed through, not overwritten."""
    connector = LeetCodeConnector()
    problem = LeetCodeProblemRaw(
        question_id="1",
        title="Two Sum",
        title_slug="two-sum",
        difficulty="Easy",
        topics=["Array", "Hash Table"],
    )
    _connect(connector, problem=problem)

    details = connector.fetch_problem_details("two-sum")

    assert details["title"] == "Two Sum"
    assert details["question_id"] == "1"
    assert details["platform"] == "LeetCode"
