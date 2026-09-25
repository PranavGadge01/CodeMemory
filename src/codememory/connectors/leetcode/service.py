"""Service-layer surface for the LeetCode account and sync lifecycle.

This is the only object a UI or CLI consumer should talk to. It wraps the Phase B
:class:`~codememory.connectors.leetcode.sync.LeetCodeSyncEngine` and the account
store, and a consumer never has to construct or call the low-level
:class:`~codememory.connectors.leetcode.client.LeetCodeClient` itself.

The surface is deliberately thin and owns no sync logic of its own:

* ``connect``    — validate the account through the supported public API and
  persist minimal, non-sensitive identity/profile metadata;
* ``sync``       — drive the existing engine, preserving its contract exactly
  (``coverage = "recent-window"``, no fabricated fields, watermark and gap
  semantics untouched), then project the outcome so it survives a restart;
* ``status``     — one object describing connection state, last sync, counts,
  coverage, window, gap and a UI-safe error;
* ``disconnect`` — drop connection and sync state while keeping every imported
  submission.

Security model: the supported public GraphQL queries need no authentication, so
this service accepts no password, cookie or token anywhere. Error text is
scrubbed before it reaches a caller, so credentials, cookies, authorization
headers and request bodies can never be displayed.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from pydantic import BaseModel, Field

from codememory.connectors.account.models import (
    AccountConnection,
    AccountStatus,
    SyncState,
    SyncStatus,
)
from codememory.connectors.account.service import AccountService
from codememory.connectors.leetcode.auth_sync import AuthenticatedSyncOrchestrator
from codememory.connectors.leetcode.authenticated_client import AuthenticatedLeetCodeClient
from codememory.connectors.leetcode.errors import LeetCodeError
from codememory.connectors.leetcode.sync import (
    UNAVAILABLE_FIELDS,
    LeetCodeSyncEngine,
)
from codememory.connectors.leetcode.vault import CredentialVault

if TYPE_CHECKING:
    from codememory.core.service import CodeMemoryService

logger = logging.getLogger(__name__)

PROVIDER = "LeetCode"

# Persisted onto the connection after each service-driven sync, so that a fresh
# process or a UI reload can still report the last result. The Phase B engine
# owns the watermark under its own keys; these are read-only projection data.
LAST_SYNC_SUMMARY_KEY = "last_sync_summary"
LAST_SUCCESSFUL_SYNC_KEY = "last_successful_sync_at"

# Error text shown to users is bounded and scrubbed. Long enough to stay
# actionable, short enough to never carry a stack trace or a request body.
MAX_ERROR_LENGTH = 400
_REDACTED = "<redacted>"

# Secret-bearing assignments: "Cookie: ...", "LEETCODE_SESSION=...",
# "Authorization: Bearer ...", "password: ..." and friends. The key name is kept
# (it tells the user what went wrong) while the value is destroyed.
_SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(leetcode_session|session_cookie|cookie|authorization|auth_token|"
    r"api[_-]?key|access[_-]?token|refresh[_-]?token|password|passwd|secret)"
    r"\b(\s*[=:]\s*)[^\s;,\]}\)\"']+"
)
# Applied before _SECRET_ASSIGNMENT: a bearer token may itself contain the
# delimiter characters that would otherwise split the match and leak the value.
_BEARER_TOKEN = re.compile(r"(?i)\bbearer\s+[^\s;,\]}\)\"']+")
# Raw GraphQL / HTTP request bodies are never appropriate in a UI message.
_REQUEST_BODY = (
    re.compile(r"""(?i)["']?query["']?\s*[=:]\s*["'][^"']*["']"""),
    re.compile(r"(?i)\bquery\s+[A-Za-z_][A-Za-z0-9_]*\s*\([^)]*\)\s*\{[^}]*\}"),
)
# An opaque blob (a token, a serialized header block) that slipped through.
_OPAQUE_BLOB = re.compile(r"(?<![A-Za-z0-9+/=_-])[A-Za-z0-9+/=_-]{20,}(?![A-Za-z0-9+/=_-])")


class LeetCodeAccountError(Exception):
    """Account/sync failure surfaced with a UI-safe message.

    Raised (never swallowed) when the underlying LeetCode transport reports a
    typed failure; its message has been through :func:`safe_error_message`.
    """


class LeetCodeAccountStatus(BaseModel):
    """Single, UI-ready view of the LeetCode account and sync state.

    Every optional field is ``None`` when unknown rather than defaulted to a
    plausible-looking number, so the UI can never imply a metric it does not have.
    """

    connected: bool = False
    username: Optional[str] = None
    display_name: Optional[str] = None
    user_avatar: Optional[str] = None
    account_status: AccountStatus = AccountStatus.NOT_CONNECTED
    sync_state: SyncState = SyncState.IDLE
    last_attempted_sync: Optional[datetime] = None
    last_successful_sync: Optional[datetime] = None
    records_discovered: Optional[int] = None
    records_imported: Optional[int] = None
    records_skipped: Optional[int] = None
    records_failed: Optional[int] = None
    coverage: Optional[str] = None
    window_limit: Optional[int] = None
    records_in_window: Optional[int] = None
    window_truncated: Optional[bool] = None
    gap_detected: Optional[bool] = None
    unavailable_fields: List[str] = Field(default_factory=list)
    # Public solving progress from the public profile query. Optional: a profile
    # fetch that failed leaves them unknown rather than zeroed.
    solved_all: Optional[int] = None
    solved_easy: Optional[int] = None
    solved_medium: Optional[int] = None
    solved_hard: Optional[int] = None
    ranking: Optional[int] = None
    last_error: Optional[str] = None
    capabilities: Dict[str, bool] = Field(default_factory=dict)


def safe_error_message(error: Any, *, max_length: int = MAX_ERROR_LENGTH) -> str:
    """Render ``error`` as a message safe to display to an end user.

    Destroys credentials, cookies, authorization headers and request bodies while
    keeping the actionable part of the message. Long messages are truncated
    rather than wrapped, so a full stack trace can never reach the UI.
    """
    text = "" if error is None else str(error)
    if not text:
        return ""

    text = _BEARER_TOKEN.sub("bearer " + _REDACTED, text)
    text = _SECRET_ASSIGNMENT.sub(r"\1\2" + _REDACTED, text)
    for pattern in _REQUEST_BODY:
        text = pattern.sub("query=" + _REDACTED, text)
    text = _OPAQUE_BLOB.sub(_REDACTED, text)

    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_length:
        text = text[: max_length - 3].rstrip() + "..."
    return text


def _parse_optional_datetime(value: Any) -> Optional[datetime]:
    """Parse a persisted timestamp, tolerating (and logging) a corrupt one."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        logger.warning("Ignoring unparseable LeetCode timestamp: %r", value)
        return None


def _meta_int(metadata: Dict[str, Any], key: str) -> Optional[int]:
    """Read a progress counter from connection metadata as an int, or ``None``.

    The persisted profile counters are display-only; a corrupt value must never
    become a plausible-looking zero in the UI.
    """
    value = metadata.get(key)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        logger.warning("Ignoring non-numeric LeetCode metadata value for %r: %r", key, value)
        return None


class LeetCodeAccountService:
    """Account + sync service surface for the LeetCode integration.

    Delegates all synchronization behaviour to the Phase B engine; it adds only
    the account lifecycle, the status projection and error scrubbing.
    """

    def __init__(
        self,
        app_service: "CodeMemoryService",
        account_service: Optional[AccountService] = None,
        *,
        client: Optional[Any] = None,
        sync_limit: Optional[int] = None,
    ) -> None:
        self._app_service = app_service
        self._account_service = account_service or AccountService()
        engine_kwargs: Dict[str, Any] = {"account_service": self._account_service}
        if client is not None:
            engine_kwargs["client"] = client
        if sync_limit is not None:
            engine_kwargs["sync_limit"] = sync_limit
        self._engine = LeetCodeSyncEngine(**engine_kwargs)

    # ───────────────────────────────────────────────────────────────────────
    # Consumer surface — nothing below exposes the transport client
    # ───────────────────────────────────────────────────────────────────────

    def is_connected(self) -> bool:
        """Whether a validated LeetCode account is currently connected."""
        return self._account_service.is_connected(PROVIDER)

    def connect(self, username: str) -> AccountConnection:
        """Validate ``username`` through the public API and store the connection.

        Idempotent: connecting an already-connected account returns the stored
        connection without a second network round trip, so a double click can
        never create a duplicate or inconsistent state.

        Raises ``ValueError`` when the identifier is unusable and
        :class:`LeetCodeAccountError` when the transport fails; in both cases no
        connection is persisted, so the account can never appear connected after
        a failed validation.
        """
        username_clean = (username or "").strip()
        if not username_clean:
            raise ValueError("LeetCode username cannot be empty.")

        existing = self._account_service.get_connection(PROVIDER)
        if (
            existing is not None
            and existing.status == AccountStatus.CONNECTED
            and (existing.username or "").lower() == username_clean.lower()
        ):
            return existing

        try:
            return self._engine.connect_account(username_clean)
        except LeetCodeError as exc:
            raise LeetCodeAccountError(safe_error_message(exc)) from exc

    def sync(self, limit: Optional[int] = None) -> SyncStatus:
        """Run one LeetCode sync through the Phase B engine.

        ``limit`` is the same local bound the engine accepts; it is not a cursor
        and is never used to page backwards.

        Never returns a fabricated success: the engine's own state machine
        decides ``SUCCESS`` / ``PARTIAL`` / ``FAILED`` and this method reports it
        unchanged. Failing to sync raises rather than returning a silent success.
        """
        result = self._engine.sync(self._app_service, limit=limit)
        self._record_sync_summary(result)
        return result

    def status(self) -> LeetCodeAccountStatus:
        """Return the current account/sync status for UI or CLI display."""
        conn = self._account_service.get_connection(PROVIDER)
        if conn is None:
            # No connection record at all: the honest answer is "not connected",
            # with no counts, no coverage and no error implied.
            return LeetCodeAccountStatus()

        summary = conn.metadata.get(LAST_SYNC_SUMMARY_KEY)
        if not isinstance(summary, dict):
            summary = {}

        return LeetCodeAccountStatus(
            connected=conn.status == AccountStatus.CONNECTED,
            username=conn.username,
            display_name=conn.display_name or conn.username,
            user_avatar=conn.user_avatar,
            account_status=conn.status,
            sync_state=conn.last_sync_status or SyncState.IDLE,
            last_attempted_sync=conn.last_sync_at,
            last_successful_sync=_parse_optional_datetime(conn.metadata.get(LAST_SUCCESSFUL_SYNC_KEY)),
            records_discovered=summary.get("records_discovered"),
            records_imported=summary.get("records_imported"),
            records_skipped=summary.get("records_skipped"),
            records_failed=summary.get("records_failed"),
            coverage=summary.get("coverage"),
            window_limit=summary.get("window_limit"),
            records_in_window=summary.get("records_in_window"),
            window_truncated=summary.get("window_truncated"),
            gap_detected=summary.get("gap_detected"),
            unavailable_fields=list(summary.get("unavailable_fields") or []),
            solved_all=_meta_int(conn.metadata, "solved_all"),
            solved_easy=_meta_int(conn.metadata, "solved_easy"),
            solved_medium=_meta_int(conn.metadata, "solved_medium"),
            solved_hard=_meta_int(conn.metadata, "solved_hard"),
            ranking=_meta_int(conn.metadata, "ranking"),
            last_error=safe_error_message(conn.last_sync_error) if conn.last_sync_error else None,
            capabilities=dict(conn.capabilities or {}),
        )

    def disconnect(self) -> bool:
        """Remove the account connection and sync state, keeping imported history.

        Submissions already imported into CodeMemory are untouched, and a later
        reconnect starts from a valid account state without needing any deletion.
        """
        return self._engine.disconnect_account()

    def store_authenticated_credentials(self, session: str, csrf_token: str) -> None:
        """Validate a session with LeetCode before securely storing it."""
        conn = self._account_service.get_connection(PROVIDER)
        account_identifier = conn.username if conn and conn.username else "default"
        vault = CredentialVault(account_identifier=account_identifier)
        if not vault.validate(session, csrf_token):
            raise LeetCodeError("LeetCode session or CSRF token has an invalid format")
        self._validate_authenticated_session(session, csrf_token)
        vault.store(session, csrf_token)

    def validate_authenticated_credentials(self) -> bool:
        """Validate stored credentials against LeetCode, not just their format."""
        conn = self._account_service.get_connection(PROVIDER)
        account_identifier = conn.username if conn and conn.username else "default"
        vault = CredentialVault(account_identifier=account_identifier)
        session, csrf_token = vault.retrieve()
        if not session or not csrf_token or not vault.validate(session, csrf_token):
            return False
        try:
            self._validate_authenticated_session(session, csrf_token)
        except LeetCodeError as exc:
            logger.info("Stored LeetCode session could not be validated: %s", safe_error_message(exc))
            return False
        return True

    def _validate_authenticated_session(self, session: str, csrf_token: str) -> None:
        """Make one authenticated read-only request without storing submissions."""
        client = AuthenticatedLeetCodeClient(
            session_cookie=session,
            csrf_token=csrf_token,
        )
        client.validate_session()

    def revoke_authenticated_credentials(self) -> None:
        """Remove stored authenticated credentials from the vault."""
        conn = self._account_service.get_connection(PROVIDER)
        account_identifier = conn.username if conn and conn.username else "default"
        vault = CredentialVault(account_identifier=account_identifier)
        vault.revoke()

    def sync_authenticated_full_history(self) -> SyncStatus:
        """Perform authenticated full-history sync using stored credentials."""
        conn = self._account_service.get_connection("LeetCode")
        username = conn.username if conn and conn.status == AccountStatus.CONNECTED else None
        account_identifier = username if username else "default"
        orchestrator = AuthenticatedSyncOrchestrator(account_identifier=account_identifier)
        return orchestrator.sync_full_history(self._app_service, username)

    # ───────────────────────────────────────────────────────────────────────
    # Internals
    # ───────────────────────────────────────────────────────────────────────

    def _record_sync_summary(self, result: SyncStatus) -> None:
        """Project the last sync onto the connection so ``status()`` outlives it.

        Pure projection: the engine's watermark, coverage and gap decisions are
        read from ``result`` and never recomputed here. The error message is
        scrubbed on the returned object as well as on the connection, so neither
        path can leak a credential.
        """
        conn = self._account_service.get_connection(PROVIDER)
        if conn is None:
            logger.warning("LeetCode connection missing after sync; summary not persisted")
            return

        details = dict(result.details or {})
        conn.metadata[LAST_SYNC_SUMMARY_KEY] = {
            "started_at": result.started_at.isoformat(),
            "finished_at": result.finished_at.isoformat() if result.finished_at else None,
            "records_discovered": result.records_discovered,
            "records_imported": result.records_added,
            "records_skipped": result.records_skipped,
            "records_failed": result.records_failed,
            "coverage": details.get("coverage"),
            "window_limit": details.get("window_limit"),
            "records_in_window": details.get("records_in_window"),
            "window_truncated": details.get("window_truncated"),
            "gap_detected": details.get("gap_detected"),
            "unavailable_fields": list(details.get("unavailable_fields") or UNAVAILABLE_FIELDS),
        }

        # A successful sync is the only run worth advertising as "last
        # successful": PARTIAL and FAILED are reported as attempts instead.
        if result.status == SyncState.SUCCESS and result.finished_at is not None:
            conn.metadata[LAST_SUCCESSFUL_SYNC_KEY] = result.finished_at.isoformat()

        if result.error_message:
            conn.last_sync_error = safe_error_message(result.error_message)
            result.error_message = conn.last_sync_error

        self._account_service.save_connection(conn)
