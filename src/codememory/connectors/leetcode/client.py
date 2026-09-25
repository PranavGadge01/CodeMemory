"""LeetCode GraphQL client wrapper providing public API connectivity for account sync.

Transport contract
------------------
CodeMemory talks to LeetCode through a single endpoint,
``https://leetcode.com/graphql``, using three read-only GraphQL queries:

* ``userPublicProfile`` — public profile, ranking and solved counts.
* ``recentAcSubmissions`` — the most recent *accepted* submissions.
* ``questionData`` — problem title, difficulty, tags and statement.

All three are public and require no authentication, which is what keeps the
integration inside LeetCode's terms: no passwords, session cookies or browser
scraping are needed or used. The optional ``session_cookie`` argument is
retained for backwards compatibility of the constructor signature only; the
public queries never send it, and it is never logged.

Robustness model
----------------
Every request is bounded by an explicit connect and read timeout. Failures are
classified as transient or permanent; only transient failures are retried, with
bounded exponential backoff and jitter, and never more than ``max_retries``
times. Permanent failures (4xx, malformed bodies, GraphQL rejections) fail
fast. On any failure ``execute_query`` returns ``None`` (unchanged behaviour)
and records a UI-safe explanation on ``last_error``.
"""

from __future__ import annotations

import http.client
import json
import logging
import random
import re
import socket
import time
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, List, Optional

from codememory.connectors.leetcode.errors import (
    LeetCodeConnectionError,
    LeetCodeError,
    LeetCodePermanentError,
    LeetCodeRateLimitError,
    LeetCodeServerError,
    LeetCodeTimeoutError,
    LeetCodeTransientError,
)
from codememory.connectors.leetcode.models import LeetCodeProblemRaw, LeetCodeSubmissionRaw

logger = logging.getLogger(__name__)

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"

# Bounded defaults. A request that cannot complete inside these windows is a
# failure to be reported, not something to block on indefinitely.
DEFAULT_CONNECT_TIMEOUT = 10.0
DEFAULT_READ_TIMEOUT = 30.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_BASE = 0.5
DEFAULT_BACKOFF_MAX = 8.0
DEFAULT_RATE_LIMIT_MAX_WAIT = 60.0

# Hard ceilings so a misconfigured client cannot degenerate into a retry storm.
MAX_ALLOWED_RETRIES = 5
MIN_ALLOWED_TIMEOUT = 0.1
MAX_ALLOWED_TIMEOUT = 300.0

# Fallback language/status used only when LeetCode omits a field. Chosen to be
# honest ("Unknown") rather than fabricated — attributing Python to a C++
# submission would silently corrupt deduplication hashes downstream.
_UNKNOWN_LANGUAGE = "Unknown"
_UNKNOWN_STATUS = "Unknown"


class _TimedHTTPSConnection(http.client.HTTPSConnection):
    """HTTPS connection with distinct connect and read timeouts.

    ``urllib`` applies one socket timeout to every phase of a request. Splitting
    them matters in practice: a slow DNS/TCP handshake and a stalled
    mid-response read are different failure modes that deserve independent
    bounds. The class attributes are set per-client by :class:`_TimedHTTPSHandler`.
    """

    connect_timeout: float = DEFAULT_CONNECT_TIMEOUT
    read_timeout: float = DEFAULT_READ_TIMEOUT

    def connect(self) -> None:
        # Apply the connect bound before the socket is opened; the value passed
        # by urllib via the constructor is deliberately overridden here.
        self.timeout = self.connect_timeout
        super().connect()
        # Switch to the read bound once the connection is established.
        if self.sock is not None:
            self.sock.settimeout(self.read_timeout)


class _TimedHTTPSHandler(urllib.request.HTTPSHandler):
    """HTTPS handler installing per-client split timeouts.

    ``handler_order`` is lower than urllib's built-ins so this handler wins for
    the ``https`` scheme instead of the default ``HTTPSHandler``.
    """

    handler_order = 400

    def __init__(self, connect_timeout: float, read_timeout: float, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._connection_class = type(
            "TimedHTTPSConnection",
            (_TimedHTTPSConnection,),
            {"connect_timeout": connect_timeout, "read_timeout": read_timeout},
        )

    def https_open(self, req: urllib.request.Request) -> http.client.HTTPResponse:
        # do_open() forwards req.timeout to the connection constructor, which
        # would collapse the split timeouts back into a single value. Clearing it
        # lets the connection class apply its own bounds.
        req.timeout = None
        return self.do_open(self._connection_class, req)


def _parse_retry_after(headers: Any) -> Optional[float]:
    """Read the server's requested delay from a ``Retry-After`` header, if any.

    Returns ``None`` when the header is absent or does not encode a number of
    seconds. The value is clamped to a sane maximum by the caller.
    """
    if headers is None:
        return None
    get = getattr(headers, "get", None)
    raw = get("Retry-After") if callable(get) else None
    if not raw:
        return None
    try:
        return max(0.0, float(str(raw).strip()))
    except (TypeError, ValueError):
        return None


def _extract_graphql_messages(errors: Any) -> List[str]:
    """Pull human-readable messages out of a GraphQL ``errors`` payload."""
    if isinstance(errors, dict):
        candidates = [errors.get("message"), errors.get("reason")]
    elif isinstance(errors, list):
        candidates = [e.get("message") for e in errors if isinstance(e, dict)]
    else:
        candidates = []

    messages = [str(m) for m in candidates if m is not None]
    return messages or ["unspecified GraphQL error"]


def _bound(value: float, minimum: float, maximum: float, name: str, default: float) -> float:
    """Clamp a numeric configuration value to an allowed range."""
    try:
        clamped = float(value)
    except (TypeError, ValueError):
        logger.warning("LeetCode client %s=%r is not a number; using %s", name, value, default)
        return default
    if clamped != clamped or clamped <= 0:  # NaN or non-positive: unusable
        return default
    if clamped < minimum or clamped > maximum:
        logger.warning(
            "LeetCode client %s=%.2f is outside [%s, %s]; clamped", name, clamped, minimum, maximum
        )
    return min(max(clamped, minimum), maximum)


class LeetCodeClient:
    """GraphQL client for the official public LeetCode GraphQL endpoint."""

    def __init__(
        self,
        session_cookie: Optional[str] = None,
        *,
        connect_timeout: float = DEFAULT_CONNECT_TIMEOUT,
        read_timeout: float = DEFAULT_READ_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_base: float = DEFAULT_BACKOFF_BASE,
        backoff_max: float = DEFAULT_BACKOFF_MAX,
        rate_limit_max_wait: float = DEFAULT_RATE_LIMIT_MAX_WAIT,
        opener: Optional[Any] = None,
        sleep_fn: Callable[[float], None] = time.sleep,
        random_fn: Callable[[float, float], float] = random.uniform,
    ) -> None:
        # Retained for constructor backwards compatibility only. The public
        # queries need no authentication; the value is never sent unless a caller
        # explicitly opts in, and it is never logged (see _headers()).
        self.session_cookie = session_cookie

        self.connect_timeout = _bound(
            connect_timeout, MIN_ALLOWED_TIMEOUT, MAX_ALLOWED_TIMEOUT, "connect_timeout", DEFAULT_CONNECT_TIMEOUT
        )
        self.read_timeout = _bound(
            read_timeout, MIN_ALLOWED_TIMEOUT, MAX_ALLOWED_TIMEOUT, "read_timeout", DEFAULT_READ_TIMEOUT
        )
        self.backoff_base = _bound(
            backoff_base, MIN_ALLOWED_TIMEOUT, MAX_ALLOWED_TIMEOUT, "backoff_base", DEFAULT_BACKOFF_BASE
        )
        self.backoff_max = _bound(
            backoff_max, MIN_ALLOWED_TIMEOUT, MAX_ALLOWED_TIMEOUT, "backoff_max", DEFAULT_BACKOFF_MAX
        )
        self.rate_limit_max_wait = _bound(
            rate_limit_max_wait, MIN_ALLOWED_TIMEOUT, MAX_ALLOWED_TIMEOUT,
            "rate_limit_max_wait", DEFAULT_RATE_LIMIT_MAX_WAIT,
        )

        # Retries are bounded from above regardless of what was requested: an
        # unbounded retry count is a self-inflicted denial of service against a
        # rate-limited endpoint.
        try:
            requested = int(max_retries)
        except (TypeError, ValueError):
            requested = DEFAULT_MAX_RETRIES
        self.max_retries = max(0, min(requested, MAX_ALLOWED_RETRIES))

        # The opener is the seam used by tests to substitute canned responses
        # and injected faults, so no test needs to touch the real network.
        self._opener = opener or urllib.request.build_opener(
            _TimedHTTPSHandler(self.connect_timeout, self.read_timeout)
        )
        self._sleep = sleep_fn
        self._random = random_fn

        # Human-readable, secret-free reason for the most recent failure. Callers
        # that want to tell the user *why* a sync failed read this instead of
        # catching an exception or parsing a stack trace.
        self.last_error: Optional[str] = None
        self.last_error_kind: Optional[str] = None

    # ───────────────────────────────────────────────────────────────────────
    # Request plumbing
    # ───────────────────────────────────────────────────────────────────────

    def _headers(self) -> Dict[str, str]:
        """Construct HTTP headers for a LeetCode GraphQL request.

        Only the cookie is ever sensitive, and it is only attached when a caller
        explicitly supplied one; the public queries never do.
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": "https://leetcode.com",
        }
        if self.session_cookie:
            headers["Cookie"] = f"LEETCODE_SESSION={self.session_cookie}"
        return headers

    @staticmethod
    def _operation_name(query: str) -> str:
        """Extract the GraphQL operation name for log lines (never the body)."""
        match = re.search(r"\b(?:query|mutation)\s+([A-Za-z_][A-Za-z0-9_]*)", query or "")
        return match.group(1) if match else "graphql"

    def _classify_url_error(self, exc: urllib.error.URLError) -> LeetCodeTransientError:
        """Map a transport-level failure to a typed, transient error.

        ``URLError`` wraps the original OSError (``socket.gaierror`` for DNS,
        ``ConnectionRefusedError``, ``TimeoutError`` for a stalled socket). All of
        these are treated as transient: they are the classic recoverable class,
        and the bounded retry loop above keeps the cost small.
        """
        reason = getattr(exc, "reason", exc)
        if isinstance(reason, (TimeoutError, socket.timeout)):
            return LeetCodeTimeoutError(
                f"LeetCode request timed out after {self.read_timeout:.0f}s read / "
                f"{self.connect_timeout:.0f}s connect"
            )
        return LeetCodeConnectionError(f"Could not reach LeetCode: {reason}")

    @staticmethod
    def _classify_http_error(exc: urllib.error.HTTPError) -> LeetCodeError:
        """Map a non-2xx HTTP status to a permanent or transient typed error."""
        code = getattr(exc, "code", 0) or 0
        if code == 429:
            retry_after = _parse_retry_after(getattr(exc, "headers", None))
            hint = f" (retry after {retry_after:.0f}s)" if retry_after is not None else ""
            return LeetCodeRateLimitError(
                "LeetCode is rate limiting requests; please retry later" + hint, retry_after=retry_after
            )
        if 500 <= code < 600:
            return LeetCodeServerError(f"LeetCode returned HTTP {code}", status_code=code)
        return LeetCodePermanentError(
            f"LeetCode rejected the request with HTTP {code} (not retried)", status_code=code
        )

    def _parse_body(self, raw: Optional[bytes]) -> Dict[str, Any]:
        """Validate a 200-class response body against the GraphQL contract.

        Raises :class:`LeetCodePermanentError` for anything that is not a
        well-formed GraphQL response object. Malformed output is permanent: the
        query is fixed, so repeating the request would return the same garbage.
        """
        text = raw.decode("utf-8", errors="replace") if raw else ""
        stripped = text.strip()

        if not stripped:
            raise LeetCodePermanentError("LeetCode returned an empty response body")

        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise LeetCodePermanentError(f"LeetCode returned a malformed JSON response: {exc.msg}")

        if not isinstance(parsed, dict):
            raise LeetCodePermanentError(
                f"LeetCode returned a non-object JSON response (got {type(parsed).__name__})"
            )

        # A GraphQL error means the query itself was rejected: permanent.
        if parsed.get("errors"):
            messages = _extract_graphql_messages(parsed["errors"])
            raise LeetCodePermanentError("LeetCode GraphQL rejected the query: " + "; ".join(messages))

        if "data" not in parsed:
            raise LeetCodePermanentError("LeetCode response had no 'data' key")

        return parsed

    def _do_post(self, payload: bytes) -> Dict[str, Any]:
        """Perform exactly one HTTP POST, classifying any failure.

        Never retries. Raises a subclass of :class:`LeetCodeError`.
        """
        try:
            operation = self._operation_name(json.loads(payload).get("query", ""))
        except (TypeError, ValueError, UnicodeDecodeError):
            operation = "graphql"

        req = urllib.request.Request(
            LEETCODE_GRAPHQL_URL, data=payload, headers=self._headers(), method="POST"
        )
        try:
            with self._opener.open(req) as response:
                status = int(getattr(response, "status", 200) or 200)
                body = response.read()
        except urllib.error.HTTPError as exc:
            safe_message = self._safe_http_error_message(exc)
            error = self._classify_http_error(exc)
            error.safe_response_message = safe_message
            logger.warning(
                "LeetCode GraphQL '%s' returned HTTP %s: %s",
                operation,
                getattr(error, "status_code", exc.code),
                safe_message,
            )
            raise error from exc
        except urllib.error.URLError as exc:
            raise self._classify_url_error(exc) from exc
        except TimeoutError as exc:
            raise LeetCodeTimeoutError(
                f"LeetCode request timed out after {self.read_timeout:.0f}s read / "
                f"{self.connect_timeout:.0f}s connect"
            ) from exc
        except OSError as exc:
            # Anything socket-level that urllib did not already wrap.
            raise LeetCodeConnectionError(f"Could not reach LeetCode: {exc}") from exc

        if not 200 <= status < 300:
            raise LeetCodePermanentError(f"LeetCode returned HTTP {status} (not retried)", status_code=status)

        return self._parse_body(body)

    def _safe_http_error_message(self, response: urllib.error.HTTPError) -> str:
        """Extract a bounded, credential-redacted message from an HTTP error.

        Never log a raw response body: retain only GraphQL error messages or
        top-level ``message``/``detail`` strings. This diagnoses 4xx responses
        without exposing credentials if the server echoes them.
        """
        try:
            raw = response.read(65537)
        except Exception:
            return "response body unavailable"
        if not raw:
            return "empty response body"
        if len(raw) > 65536:
            return "response body exceeded diagnostic size limit"

        try:
            parsed = json.loads(raw.decode("utf-8", errors="replace"))
        except (TypeError, ValueError):
            return f"non-JSON response body ({len(raw)} bytes)"

        messages: List[str] = []
        if isinstance(parsed, dict):
            errors = parsed.get("errors")
            if errors:
                messages = _extract_graphql_messages(errors)
            else:
                for key in ("message", "detail"):
                    value = parsed.get(key)
                    if isinstance(value, str):
                        messages.append(value)
        if not messages:
            return "response body contained no safe error message"

        message = "; ".join(messages)
        for secret in (getattr(self, "session_cookie", None), getattr(self, "csrf_token", None)):
            if isinstance(secret, str) and secret:
                message = message.replace(secret, "<redacted>")
        message = re.sub(r"(?i)\bbearer\s+[^\s,;]+", "Bearer <redacted>", message)
        message = re.sub(
            r"(?i)\b(leetcode_session|csrftoken|authorization|cookie)\b(\s*[=:]\s*)[^\s,;]+",
            r"\1\2<redacted>",
            message,
        )
        return message[:500]

    def _retry_delay(self, exc: LeetCodeError, attempt: int) -> float:
        """Compute the backoff delay before the next retry, in seconds.

        Exponential growth with a jitter term so that concurrent clients do not
        resynchronise their retries ("thundering herd"). A rate-limited request
        honours the server's ``Retry-After`` when provided, still capped so a
        hostile or broken server cannot stall the sync indefinitely.
        """
        if isinstance(exc, LeetCodeRateLimitError) and exc.retry_after is not None:
            return min(exc.retry_after, self.rate_limit_max_wait)

        exponential = self.backoff_base * (2 ** (attempt - 1))
        jitter = self._random(0.0, self.backoff_base)
        return min(exponential + jitter, self.backoff_max)

    def _request(self, operation: str, payload: bytes) -> Dict[str, Any]:
        """POST one GraphQL operation, retrying only transient failures.

        Retries are bounded by ``max_retries``; permanent errors escape on the
        first attempt without sleeping.
        """
        attempt = 0
        while True:
            attempt += 1
            try:
                return self._do_post(payload)
            except LeetCodePermanentError:
                raise
            except LeetCodeTransientError as exc:
                if attempt > self.max_retries:
                    raise
                delay = self._retry_delay(exc, attempt)
                logger.info(
                    "LeetCode '%s' attempt %d/%d failed transiently (%s); retrying in %.2fs",
                    operation,
                    attempt,
                    self.max_retries,
                    type(exc).__name__,
                    delay,
                )
                self._sleep(delay)

    def execute_query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Execute a GraphQL POST against the public LeetCode endpoint.

        Returns the parsed response object, or ``None`` if the request failed
        after bounded retries. On failure the reason is available on
        :attr:`last_error`; it is safe to display to end users.
        """
        operation = self._operation_name(query)
        payload = json.dumps({"query": query, "variables": variables or {}}).encode("utf-8")

        try:
            return self._request(operation, payload)
        except LeetCodeError as exc:
            # Built from status codes/categories only — no headers, cookies or
            # request bodies are included, so this is safe to surface.
            diagnostic = getattr(exc, "safe_response_message", None)
            self.last_error = str(exc)
            if diagnostic:
                self.last_error = f"{self.last_error}: {diagnostic}"
            self.last_error_kind = type(exc).__name__
            logger.warning("LeetCode GraphQL '%s' failed: %s", operation, exc)
            return None

    # ───────────────────────────────────────────────────────────────────────
    # Public API operations
    # ───────────────────────────────────────────────────────────────────────

    @staticmethod
    def _graphql_data(result: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Return the response's ``data`` object, or ``None`` when unusable.

        ``_parse_body`` guarantees a ``data`` *key* exists, but GraphQL permits
        ``"data": null`` (and a broken server can send a non-object), so callers
        must not assume it is a dict.
        """
        if not isinstance(result, dict):
            return None
        data = result.get("data")
        return data if isinstance(data, dict) else None

    def fetch_user_profile(self, username: str) -> Optional[Dict[str, Any]]:
        """Fetch public profile, avatar, ranking, and solved breakdown via GraphQL.

        Returns ``None`` when the account does not exist or the request failed.
        """
        query = """
        query userPublicProfile($username: String!) {
            matchedUser(username: $username) {
                username
                profile {
                    realName
                    userAvatar
                    ranking
                }
                submitStats {
                    acSubmissionNum {
                        difficulty
                        count
                    }
                }
            }
        }
        """
        result = self.execute_query(query, {"username": username})
        data = self._graphql_data(result)
        if data is None or not data.get("matchedUser"):
            return None

        user_data = data["matchedUser"]
        if not isinstance(user_data, dict):
            return None

        profile = user_data.get("profile") or {}
        if not isinstance(profile, dict):
            profile = {}

        stats_root = user_data.get("submitStats") or {}
        stats = stats_root.get("acSubmissionNum", []) if isinstance(stats_root, dict) else []
        if not isinstance(stats, list):
            stats = []

        difficulty_counts = {
            item.get("difficulty"): item.get("count", 0)
            for item in stats
            if isinstance(item, dict) and item.get("difficulty") is not None
        }

        return {
            "username": user_data.get("username") or username,
            "real_name": profile.get("realName"),
            "user_avatar": profile.get("userAvatar"),
            "ranking": profile.get("ranking"),
            "solved_all": difficulty_counts.get("All", 0),
            "solved_easy": difficulty_counts.get("Easy", 0),
            "solved_medium": difficulty_counts.get("Medium", 0),
            "solved_hard": difficulty_counts.get("Hard", 0),
        }

    def fetch_user_submissions(self, username: str, limit: int = 20) -> List[LeetCodeSubmissionRaw]:
        """Fetch recent accepted submissions via the public GraphQL query.

        Returns an empty list when the account has no submissions or the request
        failed. Malformed individual entries are skipped rather than aborting the
        whole batch.
        """
        query = """
        query recentAcSubmissions($username: String!, $limit: Int!) {
            recentAcSubmissionList(username: $username, limit: $limit) {
                id
                title
                titleSlug
                timestamp
                statusDisplay
                lang
            }
        }
        """
        result = self.execute_query(query, {"username": username, "limit": limit})
        data = self._graphql_data(result)
        if not data:
            return []

        raw_list = data.get("recentAcSubmissionList")
        if not raw_list or not isinstance(raw_list, list):
            return []

        raw_submissions: List[LeetCodeSubmissionRaw] = []
        for index, item in enumerate(raw_list):
            if not isinstance(item, dict):
                logger.warning("Skipping malformed LeetCode submission at index %d (not an object)", index)
                continue
            try:
                raw_submissions.append(
                    LeetCodeSubmissionRaw(
                        id=item.get("id"),
                        submission_id=item.get("id"),
                        title=item.get("title") or "",
                        title_slug=item.get("titleSlug"),
                        # No fabrication: a missing language must not default to
                        # Python, or the dedup hash would misattribute the record.
                        language=item.get("lang") or _UNKNOWN_LANGUAGE,
                        status=item.get("statusDisplay") or _UNKNOWN_STATUS,
                        timestamp=item.get("timestamp"),
                    )
                )
            except (TypeError, ValueError) as exc:
                logger.warning("Skipping malformed LeetCode submission at index %d: %s", index, exc)
                continue
        return raw_submissions

    def fetch_problem_details(self, problem_slug: str) -> Optional[LeetCodeProblemRaw]:
        """Fetch problem details (title, difficulty, topics, content) via GraphQL.

        Returns ``None`` when the problem is unknown or the request failed.
        """
        query = """
        query questionData($titleSlug: String!) {
            question(titleSlug: $titleSlug) {
                questionId
                title
                titleSlug
                difficulty
                content
                topicTags {
                    name
                }
            }
        }
        """
        result = self.execute_query(query, {"titleSlug": problem_slug})
        data = self._graphql_data(result)
        if data is None or not data.get("question"):
            return None

        q = data["question"]
        if not isinstance(q, dict):
            return None

        topic_tags = q.get("topicTags")
        topics = (
            [t["name"] for t in topic_tags if isinstance(t, dict) and "name" in t]
            if isinstance(topic_tags, list)
            else []
        )
        return LeetCodeProblemRaw(
            id=q.get("questionId"),
            question_id=q.get("questionId"),
            title=q.get("title") or problem_slug.replace("-", " ").title(),
            title_slug=q.get("titleSlug") or problem_slug,
            difficulty=q.get("difficulty"),
            topics=topics,
            url=f"https://leetcode.com/problems/{problem_slug}/",
            content=q.get("content"),
        )
