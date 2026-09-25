"""Typed transport errors for the LeetCode GraphQL client.

The client separates failures into two families so that retry policy can be
decided mechanically instead of by inspecting strings:

* :class:`LeetCodeTransientError` — the request *may* succeed if repeated.
  Network conditions, rate limiting and server-side faults belong here.
* :class:`LeetCodePermanentError` — the request will fail again as posed.
  Client errors, malformed bodies and GraphQL rejections belong here.

Messages attached to these exceptions are safe to surface in the UI: they are
built from status codes and error categories, never from request bodies,
headers or credentials.
"""

from typing import Optional


class LeetCodeError(Exception):
    """Base class for every LeetCode transport failure."""


class CredentialVaultError(LeetCodeError):
    """Errors related to credential vault operations."""


class LeetCodeTransientError(LeetCodeError):
    """A failure that may succeed on retry (network, timeout, 5xx, rate limit)."""


class LeetCodeConnectionError(LeetCodeTransientError):
    """DNS resolution or TCP connection to LeetCode failed."""


class LeetCodeTimeoutError(LeetCodeTransientError):
    """The request exceeded its connect or read timeout."""


class LeetCodeServerError(LeetCodeTransientError):
    """LeetCode returned a server-side HTTP error (5xx)."""

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class LeetCodeRateLimitError(LeetCodeTransientError):
    """LeetCode declined to serve the request because of rate limiting.

    ``retry_after`` carries the server's requested delay in seconds when it
    advertised one via the ``Retry-After`` header.
    """

    def __init__(self, message: str, retry_after: Optional[float] = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class LeetCodePermanentError(LeetCodeError):
    """A failure that will recur if the identical request is repeated.

    Client errors (4xx other than 429), malformed bodies and GraphQL query
    rejections are permanent: retrying them wastes budget and, for rate-limited
    endpoints, makes things worse.
    """

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code
