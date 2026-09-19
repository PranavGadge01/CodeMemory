"""Network-hardening tests for LeetCodeClient.

None of these tests touch the network. Every response and fault is injected
through the client's ``opener`` seam, so transient/permanent classification and
backoff timing are verified deterministically rather than against a live,
rate-limited third party.
"""

import io
import json
import logging
import socket
import urllib.error
from email.message import Message
from typing import Any, List

import pytest

from codememory.connectors.leetcode.client import (
    DEFAULT_BACKOFF_BASE,
    DEFAULT_CONNECT_TIMEOUT,
    DEFAULT_MAX_RETRIES,
    DEFAULT_RATE_LIMIT_MAX_WAIT,
    DEFAULT_READ_TIMEOUT,
    MAX_ALLOWED_RETRIES,
    LeetCodeClient,
)
from codememory.connectors.leetcode.errors import (
    LeetCodeConnectionError,
    LeetCodePermanentError,
    LeetCodeRateLimitError,
    LeetCodeServerError,
    LeetCodeTimeoutError,
)

GRAPHQL_URL = "https://leetcode.com/graphql"

_PROFILE_OK = {
    "data": {
        "matchedUser": {
            "username": "alice",
            "profile": {"realName": "Alice", "userAvatar": "https://x/a.png", "ranking": 1234},
            "submitStats": {
                "acSubmissionNum": [
                    {"difficulty": "All", "count": 42},
                    {"difficulty": "Easy", "count": 20},
                    {"difficulty": "Medium", "count": 15},
                    {"difficulty": "Hard", "count": 7},
                ]
            },
        }
    }
}

_SUBMISSIONS_OK = {
    "data": {
        "recentAcSubmissionList": [
            {"id": "1001", "title": "Two Sum", "titleSlug": "two-sum",
             "timestamp": "1700007200", "statusDisplay": "AC", "lang": "python3"},
            {"id": "1002", "title": "3Sum", "titleSlug": "3sum",
             "timestamp": "1700100000", "statusDisplay": "AC", "lang": "cpp"},
        ]
    }
}

_PROBLEM_OK = {
    "data": {
        "question": {
            "questionId": "1",
            "title": "Two Sum",
            "titleSlug": "two-sum",
            "difficulty": "Easy",
            "content": "<p>Given an array...</p>",
            "topicTags": [{"name": "Array"}, {"name": "Hash Table"}],
        }
    }
}


# ─────────────────────────────────────────────────────────────────────────────
# Test doubles
# ─────────────────────────────────────────────────────────────────────────────


class _FakeResponse:
    """Minimal stand-in for http.client.HTTPResponse."""

    def __init__(self, status: int = 200, body: bytes = b"", headers: Message | None = None):
        self.status = status
        self._body = body
        self.headers = headers if headers is not None else Message()

    def read(self, *args: Any, **kwargs: Any) -> bytes:
        return self._body

    def close(self) -> None:
        pass

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *exc: Any) -> bool:
        return False


class _FakeOpener:
    """Replays a scripted sequence of responses or injected faults.

    Each script entry is a response, an exception to raise, or a callable
    receiving the request (used when the test needs to inspect what was sent).
    """

    def __init__(self, *script: Any):
        self.script: List[Any] = list(script)
        self.requests: List[urllib.request.Request] = []  # noqa: F821  (type hint only)

    def open(self, req: Any, timeout: Any = None) -> _FakeResponse:
        self.requests.append(req)
        if not self.script:
            raise AssertionError("LeetCodeClient made an unexpected extra request")
        item = self.script.pop(0)
        if callable(item) and not isinstance(item, BaseException):
            item = item(req)
        if isinstance(item, BaseException):
            raise item
        return item


def _body(payload: Any) -> bytes:
    return json.dumps(payload).encode("utf-8")


def _ok(payload: Any) -> _FakeResponse:
    return _FakeResponse(200, _body(payload))


def _http_error(code: int, msg: str = "Error", body: bytes = b"", headers: Message | None = None) -> urllib.error.HTTPError:
    hdrs = headers if headers is not None else Message()
    return urllib.error.HTTPError(GRAPHQL_URL, code, msg, hdrs, io.BytesIO(body))


def _rate_limit(retry_after: float | None) -> urllib.error.HTTPError:
    headers = Message()
    if retry_after is not None:
        headers["Retry-After"] = str(retry_after)
    return _http_error(429, "Too Many Requests", headers=headers)


class _Recorder:
    """Captures sleep calls so backoff timing is asserted without waiting."""

    def __init__(self) -> None:
        self.delays: List[float] = []

    def sleep(self, seconds: float) -> None:
        self.delays.append(seconds)

    @staticmethod
    def no_jitter(low: float, high: float) -> float:
        return low


def _client(*script: Any, **kwargs: Any) -> tuple[LeetCodeClient, _FakeOpener, _Recorder]:
    recorder = _Recorder()
    opener = _FakeOpener(*script)
    defaults = dict(sleep_fn=recorder.sleep, random_fn=_Recorder.no_jitter)
    defaults.update(kwargs)
    return LeetCodeClient(opener=opener, **defaults), opener, recorder


def _exhaust(fault: Any) -> List[Any]:
    """Repeat a fault enough times to exhaust the default retry budget."""
    return [fault] * (DEFAULT_MAX_RETRIES + 1)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Happy paths
# ─────────────────────────────────────────────────────────────────────────────


def test_fetch_user_profile_success():
    client, opener, _ = _client(_ok(_PROFILE_OK))
    profile = client.fetch_user_profile("alice")

    assert profile == {
        "username": "alice",
        "real_name": "Alice",
        "user_avatar": "https://x/a.png",
        "ranking": 1234,
        "solved_all": 42,
        "solved_easy": 20,
        "solved_medium": 15,
        "solved_hard": 7,
    }
    assert len(opener.requests) == 1
    assert client.last_error is None


def test_fetch_user_submissions_success():
    client, opener, _ = _client(_ok(_SUBMISSIONS_OK))
    subs = client.fetch_user_submissions("alice", limit=2)

    assert len(subs) == 2
    assert subs[0].id == "1001"
    assert subs[0].title == "Two Sum"
    assert subs[0].title_slug == "two-sum"
    assert subs[0].submission_id == "1001"
    assert subs[0].timestamp == "1700007200"
    assert subs[1].language == "cpp"
    assert len(opener.requests) == 1


def test_fetch_problem_details_success():
    client, _, _ = _client(_ok(_PROBLEM_OK))
    problem = client.fetch_problem_details("two-sum")

    assert problem is not None
    assert problem.id == "1"
    assert problem.title == "Two Sum"
    assert problem.difficulty == "Easy"
    assert problem.topics == ["Array", "Hash Table"]
    assert problem.url == "https://leetcode.com/problems/two-sum/"


def test_request_is_a_json_post_to_the_graphql_endpoint():
    client, opener, _ = _client(lambda req: _ok(_PROFILE_OK))
    client.fetch_user_profile("alice")

    req = opener.requests[0]
    assert req.get_method() == "POST"
    assert req.get_full_url() == GRAPHQL_URL
    assert req.get_header("Content-type") == "application/json"
    # The GraphQL query and variables travel in the body.
    body = json.loads(req.data.decode("utf-8"))
    assert "query" in body and "variables" in body
    assert body["variables"] == {"username": "alice"}


def test_transient_failure_then_success_recovers():
    """One hiccup must not fail a request that would succeed on retry."""
    client, opener, recorder = _client(
        _http_error(503, "Service Unavailable"),
        _ok(_PROFILE_OK),
    )
    assert client.fetch_user_profile("alice") is not None
    assert len(opener.requests) == 2
    assert len(recorder.delays) == 1


# ─────────────────────────────────────────────────────────────────────────────
# 2. Empty / null data (valid GraphQL, nothing to import)
# ─────────────────────────────────────────────────────────────────────────────


def test_unknown_user_returns_none():
    client, _, _ = _client(_ok({"data": {"matchedUser": None}}))
    assert client.fetch_user_profile("ghost_user_12345") is None


def test_user_with_no_submissions_returns_empty_list():
    client, _, _ = _client(_ok({"data": {"recentAcSubmissionList": []}}))
    assert client.fetch_user_submissions("alice") == []


def test_unknown_problem_returns_none():
    client, _, _ = _client(_ok({"data": {"question": None}}))
    assert client.fetch_problem_details("no-such-problem") is None


def test_null_submission_list_returns_empty_list():
    client, _, _ = _client(_ok({"data": {"recentAcSubmissionList": None}}))
    assert client.fetch_user_submissions("alice") == []


# ─────────────────────────────────────────────────────────────────────────────
# 3. Transient failures are retried
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "fault,fabric",
    [
        (urllib.error.URLError(socket.gaierror("Name or service not known")), LeetCodeConnectionError),
        (urllib.error.URLError(ConnectionRefusedError("connection refused")), LeetCodeConnectionError),
        (urllib.error.URLError(TimeoutError("timed out")), LeetCodeTimeoutError),
        (_http_error(500, "Internal Server Error"), LeetCodeServerError),
        (_http_error(502, "Bad Gateway"), LeetCodeServerError),
        (_http_error(503, "Service Unavailable"), LeetCodeServerError),
    ],
)
def test_transient_failures_are_retried_then_reported(fault, fabric):
    client, opener, recorder = _client(fault, fault, fault, fault)
    assert client.fetch_user_profile("alice") is None

    # DEFAULT_MAX_RETRIES attempts plus the original attempt.
    assert len(opener.requests) == DEFAULT_MAX_RETRIES + 1
    assert len(recorder.delays) == DEFAULT_MAX_RETRIES
    assert client.last_error_kind == fabric.__name__


def test_rate_limit_is_retried_honouring_retry_after():
    client, opener, recorder = _client(_rate_limit(7.0), _ok(_PROFILE_OK))
    assert client.fetch_user_profile("alice") is not None

    assert len(opener.requests) == 2
    assert recorder.delays == [7.0]


def test_rate_limit_retry_after_is_capped():
    """A hostile Retry-After cannot stall the sync indefinitely."""
    client, _, recorder = _client(_rate_limit(99999.0), _ok(_PROFILE_OK))
    client.fetch_user_profile("alice")

    assert recorder.delays == [DEFAULT_RATE_LIMIT_MAX_WAIT]


def test_rate_limit_without_retry_after_uses_exponential_backoff():
    client, _, recorder = _client(_rate_limit(None), _rate_limit(None), _ok(_PROFILE_OK))
    client.fetch_user_profile("alice")

    assert recorder.delays == [DEFAULT_BACKOFF_BASE, DEFAULT_BACKOFF_BASE * 2]


def test_backoff_grows_exponentially_and_is_capped():
    client, _, recorder = _client(
        *([_http_error(500)] * (DEFAULT_MAX_RETRIES + 1)),
        backoff_base=1.0,
        backoff_max=3.0,
    )
    client.fetch_user_profile("alice")

    # 1, 2, then capped at 3 — bounded growth, never unbounded.
    assert recorder.delays == [1.0, 2.0, 3.0]


def test_backoff_adds_jitter():
    """Jitter de-synchronises retries; it must be applied, not zeroed."""
    seen = []

    def jitter(low: float, high: float) -> float:
        seen.append((low, high))
        return 0.25

    opener = _FakeOpener(*([_http_error(500)] * 2), _ok(_PROFILE_OK))
    recorder = _Recorder()
    client = LeetCodeClient(opener=opener, sleep_fn=recorder.sleep, random_fn=jitter)
    client.fetch_user_profile("alice")

    # Each delay is exponential + jitter, within the configured envelope.
    assert recorder.delays == [
        DEFAULT_BACKOFF_BASE + 0.25,
        DEFAULT_BACKOFF_BASE * 2 + 0.25,
    ]
    assert seen and seen[0][1] == DEFAULT_BACKOFF_BASE


def test_max_retries_zero_is_a_single_attempt():
    client, opener, recorder = _client(_http_error(500), max_retries=0)
    assert client.fetch_user_profile("alice") is None

    assert len(opener.requests) == 1
    assert recorder.delays == []


def test_retries_are_capped_even_when_configured_higher():
    client, opener, recorder = _client(*([_http_error(500)] * 50), max_retries=99)
    client.fetch_user_profile("alice")

    assert len(opener.requests) == MAX_ALLOWED_RETRIES + 1
    assert len(recorder.delays) == MAX_ALLOWED_RETRIES


# ─────────────────────────────────────────────────────────────────────────────
# 4. Permanent failures are NOT retried
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("code", [400, 401, 403, 404, 405, 422])
def test_permanent_4xx_errors_fail_fast(code):
    client, opener, recorder = _client(_http_error(code))
    assert client.fetch_user_profile("alice") is None

    assert len(opener.requests) == 1, "permanent client errors must not be retried"
    assert recorder.delays == []
    assert client.last_error_kind == "LeetCodePermanentError"
    assert str(code) in client.last_error


def test_malformed_json_is_not_retried():
    client, opener, recorder = _client(_FakeResponse(200, b"not json at all"))
    assert client.fetch_user_profile("alice") is None

    assert len(opener.requests) == 1
    assert "malformed JSON" in client.last_error


def test_empty_body_is_not_retried():
    client, opener, recorder = _client(_FakeResponse(200, b""))
    assert client.fetch_user_profile("alice") is None

    assert len(opener.requests) == 1
    assert "empty response body" in client.last_error


@pytest.mark.parametrize("payload", [[], "unexpected", 42, None])
def test_non_object_json_is_not_retried(payload):
    client, opener, _ = _client(_FakeResponse(200, _body(payload)))
    assert client.fetch_user_profile("alice") is None
    assert len(opener.requests) == 1


def test_graphql_errors_are_not_retried():
    client, opener, recorder = _client(
        _ok({"errors": [{"message": "Field 'nope' doesn't exist on type 'Query'"}]})
    )
    assert client.fetch_user_profile("alice") is None

    assert len(opener.requests) == 1
    assert "GraphQL rejected the query" in client.last_error
    assert "Field 'nope'" in client.last_error


def test_graphql_error_without_message_still_reports():
    client, _, _ = _client(_ok({"errors": [{"code": "INTERNAL"}]}))
    assert client.fetch_user_profile("alice") is None
    assert "unspecified GraphQL error" in client.last_error


def test_response_without_data_key_is_permanent():
    client, opener, _ = _client(_FakeResponse(200, _body({"unrelated": 1})))
    assert client.fetch_user_profile("alice") is None
    assert len(opener.requests) == 1
    assert "no 'data' key" in client.last_error


# ─────────────────────────────────────────────────────────────────────────────
# 5. Malformed / partial payload handling inside a valid response
# ─────────────────────────────────────────────────────────────────────────────


def test_malformed_submission_entries_are_skipped_not_fatal():
    """One bad entry must not destroy the whole batch."""
    payload = {
        "data": {
            "recentAcSubmissionList": [
                "not-an-object",
                {"id": "1001", "title": "Two Sum", "titleSlug": "two-sum", "lang": "python3"},
                {"title": "No id", "lang": "java"},
                {"id": "1002", "title": "3Sum", "titleSlug": "3sum", "lang": "cpp"},
            ]
        }
    }
    client, _, _ = _client(_ok(payload))
    subs = client.fetch_user_submissions("alice")

    assert [s.id for s in subs] == ["1001", None, "1002"]


def test_missing_language_is_never_fabricated_as_python():
    """Defaulting a missing language to python3 would corrupt dedup hashes."""
    payload = {"data": {"recentAcSubmissionList": [{"id": "1", "title": "T", "titleSlug": "t"}]}}
    client, _, _ = _client(_ok(payload))

    subs = client.fetch_user_submissions("alice")
    assert subs[0].language == "Unknown"
    assert subs[0].status == "Unknown"


def test_non_list_submission_list_is_tolerated():
    client, _, _ = _client(_ok({"data": {"recentAcSubmissionList": {"id": "1"}}}))
    assert client.fetch_user_submissions("alice") == []


def test_non_dict_matched_user_is_tolerated():
    client, _, _ = _client(_ok({"data": {"matchedUser": "garbage"}}))
    assert client.fetch_user_profile("alice") is None


def test_profile_with_missing_stats_still_returns_username():
    client, _, _ = _client(_ok({"data": {"matchedUser": {"username": "alice"}}}))
    profile = client.fetch_user_profile("alice")
    assert profile["username"] == "alice"
    assert profile["solved_all"] == 0


@pytest.mark.parametrize("data", [None, "unexpected", 42, []])
def test_null_or_non_object_data_is_tolerated_for_profile(data):
    """GraphQL permits "data": null; it must not become an AttributeError."""
    client, _, _ = _client(_ok({"data": data}))
    assert client.fetch_user_profile("alice") is None


@pytest.mark.parametrize("data", [None, "unexpected", 42])
def test_null_or_non_object_data_is_tolerated_for_submissions(data):
    client, _, _ = _client(_ok({"data": data}))
    assert client.fetch_user_submissions("alice") == []


@pytest.mark.parametrize("data", [None, "unexpected", 42])
def test_null_or_non_object_data_is_tolerated_for_problem(data):
    client, _, _ = _client(_ok({"data": data}))
    assert client.fetch_problem_details("two-sum") is None


def test_problem_with_unusual_topic_tags_is_tolerated():
    client, _, _ = _client(
        _ok({"data": {"question": {"questionId": "1", "title": "T", "topicTags": "oops"}}})
    )
    problem = client.fetch_problem_details("t")
    assert problem is not None
    assert problem.topics == []


def test_problem_title_falls_back_to_slug_when_absent():
    client, _, _ = _client(_ok({"data": {"question": {"questionId": "1", "titleSlug": "two-sum"}}}))
    problem = client.fetch_problem_details("two-sum")
    assert problem is not None
    assert problem.title == "Two Sum"


# ─────────────────────────────────────────────────────────────────────────────
# 6. Timeouts and configuration bounds
# ─────────────────────────────────────────────────────────────────────────────


def test_default_timeouts_are_explicit_and_bounded():
    client = LeetCodeClient()
    assert client.connect_timeout == DEFAULT_CONNECT_TIMEOUT
    assert client.read_timeout == DEFAULT_READ_TIMEOUT
    assert client.max_retries == DEFAULT_MAX_RETRIES


@pytest.mark.parametrize(
    "kwargs,attr,expected",
    [
        ({"connect_timeout": 0}, "connect_timeout", DEFAULT_CONNECT_TIMEOUT),
        ({"connect_timeout": -5}, "connect_timeout", DEFAULT_CONNECT_TIMEOUT),
        ({"read_timeout": 1e9}, "read_timeout", 300.0),
        ({"max_retries": -1}, "max_retries", 0),
        ({"max_retries": 1000}, "max_retries", MAX_ALLOWED_RETRIES),
    ],
)
def test_out_of_range_config_falls_back_or_clamps(kwargs, attr, expected):
    client = LeetCodeClient(opener=_FakeOpener(), **kwargs)
    assert getattr(client, attr) == expected


def test_non_numeric_config_is_rejected():
    client = LeetCodeClient(opener=_FakeOpener(), connect_timeout="soon")
    assert client.connect_timeout == DEFAULT_CONNECT_TIMEOUT


def test_nan_config_is_rejected():
    """NaN compares false against every bound, so it must be rejected explicitly."""
    client = LeetCodeClient(opener=_FakeOpener(), connect_timeout=float("nan"), max_retries=99)
    assert client.connect_timeout == DEFAULT_CONNECT_TIMEOUT


def test_split_timeouts_are_installed_on_the_connection(monkeypatch):
    """The handler must install separate connect and read bounds on the socket.

    urllib applies a single timeout to every phase; splitting them is what keeps
    a slow handshake from being mistaken for a stalled body (and vice versa).
    """
    from codememory.connectors.leetcode.client import _TimedHTTPSHandler

    handler = _TimedHTTPSHandler(connect_timeout=3.0, read_timeout=17.0)
    connection_class = handler._connection_class

    assert connection_class.connect_timeout == 3.0
    assert connection_class.read_timeout == 17.0
    assert connection_class.read_timeout != connection_class.connect_timeout


def test_custom_handler_wins_the_https_scheme():
    """The split-timeout handler must actually serve https requests.

    urllib registers its own HTTPSHandler; if ours lost precedence the timeouts
    would silently revert to urllib's single-value timeout and every assertion
    above would be moot.
    """
    from codememory.connectors.leetcode import client as client_module
    from codememory.connectors.leetcode.client import _TimedHTTPSHandler

    client = LeetCodeClient()
    chain = client._opener.handle_open.get("https", [])
    assert chain, "no handler registered for the https scheme"
    assert isinstance(chain[0], _TimedHTTPSHandler)
    assert all(isinstance(h, _TimedHTTPSHandler) for h in chain)
    assert not any(
        type(h) is client_module.urllib.request.HTTPSHandler for h in chain
    )


def test_connect_bound_applied_before_socket_open(monkeypatch):
    """The connection must use the connect timeout while opening the socket.

    Stands in for the socket handshake without doing any real I/O: what matters
    is which timeout value was in force when the socket was opened, and which one
    applies to reads afterwards.
    """
    from codememory.connectors.leetcode import client as client_module

    captured: dict = {}

    class _FakeSock:
        def __init__(self) -> None:
            self.timeout: float | None = None

        def gettimeout(self) -> float | None:
            return self.timeout

        def settimeout(self, value: float | None) -> None:
            self.timeout = value

    def fake_handshake(self) -> None:
        # Replaces HTTPSConnection.connect(): opens the socket using self.timeout.
        captured["timeout_at_connect"] = self.timeout
        self.sock = _FakeSock()

    # _TimedHTTPSConnection.connect() calls super().connect(); replacing the
    # parent keeps the TLS handshake from touching the network.
    monkeypatch.setattr(client_module.http.client.HTTPSConnection, "connect", fake_handshake)

    client = LeetCodeClient(connect_timeout=2.0, read_timeout=11.0)

    # The opener was built with a handler bound to these values.
    handler = next(
        h for h in client._opener.handlers if isinstance(h, client_module._TimedHTTPSHandler)
    )
    connection = handler._connection_class("leetcode.com")
    connection.connect()

    assert captured["timeout_at_connect"] == 2.0, "handshake must use the connect timeout"
    assert connection.sock.gettimeout() == 11.0, "reads must use the read timeout"


# ─────────────────────────────────────────────────────────────────────────────
# 7. Secret safety
# ─────────────────────────────────────────────────────────────────────────────


def test_session_cookie_is_never_logged(caplog):
    """A leaked cookie would compromise the user's LeetCode account."""
    secret = "SUPER_SECRET_SESSION_VALUE"
    client = LeetCodeClient(session_cookie=secret, opener=_FakeOpener(*_exhaust(_http_error(500))))

    with caplog.at_level(logging.DEBUG, logger="codememory.connectors.leetcode.client"):
        client.fetch_user_profile("alice")

    rendered = "\n".join(rec.getMessage() for rec in caplog.records)
    assert secret not in rendered
    assert secret not in (client.last_error or "")


def test_request_body_and_headers_are_never_logged(caplog):
    """Query text, variables and headers stay out of logs."""
    client, _, _ = _client(*_exhaust(_http_error(500)))

    with caplog.at_level(logging.DEBUG, logger="codememory.connectors.leetcode.client"):
        client.fetch_user_profile("alice")

    rendered = "\n".join(rec.getMessage() for rec in caplog.records)
    assert "matchedUser" not in rendered
    assert "Cookie" not in rendered
    assert "alice" not in rendered


def test_last_error_is_safe_to_display():
    """The UI surfaces this directly; it must carry no secrets or stack traces."""
    client, _, _ = _client(_http_error(403, "Forbidden"))
    client.fetch_user_profile("alice")

    assert client.last_error is not None
    assert "Traceback" not in client.last_error
    assert "403" in client.last_error


# ─────────────────────────────────────────────────────────────────────────────
# 8. Error typing for callers
# ─────────────────────────────────────────────────────────────────────────────


def test_execute_query_returns_none_on_permanent_failure():
    client, _, _ = _client(_FakeResponse(200, b"garbage"))
    assert client.execute_query("query namedQ($a: Int!) { a }") is None


def test_operation_name_is_used_in_log_lines(caplog):
    client, _, _ = _client(*_exhaust(_http_error(500)))

    with caplog.at_level(logging.INFO, logger="codememory.connectors.leetcode.client"):
        client.execute_query("query userPublicProfile($username: String!) { x }", {"username": "a"})

    assert any("userPublicProfile" in rec.getMessage() for rec in caplog.records)


def test_unnamed_query_logs_a_generic_operation(caplog):
    client, _, _ = _client(*_exhaust(_http_error(500)))

    with caplog.at_level(logging.INFO, logger="codememory.connectors.leetcode.client"):
        client.execute_query("{ viewer { login } }")

    assert any("'graphql'" in rec.getMessage() for rec in caplog.records)


def test_errors_module_exposes_retryable_classification():
    """Transient vs permanent must be decidable without parsing strings."""
    from codememory.connectors.leetcode.errors import LeetCodeError, LeetCodeTransientError

    for cls in (LeetCodeConnectionError, LeetCodeTimeoutError, LeetCodeServerError, LeetCodeRateLimitError):
        assert issubclass(cls, LeetCodeTransientError)
        assert issubclass(cls, LeetCodeError)

    assert not issubclass(LeetCodePermanentError, LeetCodeTransientError)
