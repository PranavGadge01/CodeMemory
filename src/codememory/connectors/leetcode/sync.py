"""LeetCode Sync Engine coordinating profile, progress, submission sync, and memory indexing.

Sync contract
-------------
The supported public LeetCode API exposes only a server-bounded window of the
most recent *accepted* submissions. It provides no source code, no runtime and no
memory, and no cursor for paging further back. This engine therefore:

* persists records exactly as the API describes them, with empty code and null
  metrics rather than fabricated stand-ins;
* never claims full history — ``SyncStatus.details["coverage"]`` is always
  ``"recent-window"``;
* keeps a local watermark of what has already been persisted. The watermark is a
  purely local bookkeeping value and is NEVER sent to LeetCode as a ``since`` or
  ``after`` parameter — the supported API has no such parameter;
* detects (but does not attempt to recover) gaps where submissions fell outside
  the server-bounded window between two syncs.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Optional

from codememory.connectors.account.models import AccountConnection, AccountStatus, SyncState, SyncStatus
from codememory.connectors.account.service import AccountService
from codememory.connectors.leetcode.capabilities import LEETCODE_CAPABILITIES
from codememory.connectors.leetcode.client import LeetCodeClient
from codememory.connectors.leetcode.mapper import LeetCodeMapper
from codememory.connectors.leetcode.models import LeetCodeSubmissionRaw
from codememory.domain.exceptions import ProblemNotFoundError
from codememory.domain.models import generate_slug

logger = logging.getLogger(__name__)

# The supported public endpoint returns a server-bounded recent window. 20 is the
# practical bound the public API serves; asking for more does not yield more.
DEFAULT_SYNC_LIMIT = 20

# Metadata keys used to persist the local watermark inside AccountConnection.
WATERMARK_KEY_ID = "latest_external_id"
WATERMARK_KEY_TS = "latest_persisted_timestamp"

# Fields the supported public API cannot supply for a synced submission. Reported
# on every sync so the UI can never imply metrics exist when they do not.
UNAVAILABLE_FIELDS = ["code", "runtime_ms", "memory_mb"]


def _external_id_sort_key(external_id: Optional[str]) -> tuple[int, str]:
    """Ordering key for a CodeMemory external submission id.

    LeetCode submission ids are monotonically increasing, so the numeric value is
    the true order; the raw string is kept as a tie-break for non-numeric ids.
    Parsing numerically matters: lexicographic order would place ``leetcode_9``
    after ``leetcode_10``.
    """
    if not external_id:
        return (-1, "")
    raw = external_id
    if raw.startswith("leetcode_"):
        raw = raw[len("leetcode_") :]
    try:
        return (int(raw), "")
    except ValueError:
        return (-1, raw)


def _record_key(timestamp: Optional[datetime], external_id: Optional[str]) -> tuple[float, tuple[int, str]]:
    """Ordering tuple for a submission: timestamp first, external id as tie-break.

    Timestamps are NOT unique — a user may submit two problems in the same
    second — so the pair is the identity of order, never the timestamp alone.
    """
    if timestamp is None:
        ts = 0.0
    else:
        ts = timestamp.astimezone(timezone.utc).timestamp() if timestamp.tzinfo else timestamp.replace(
            tzinfo=timezone.utc
        ).timestamp()
    return (ts, _external_id_sort_key(external_id))


class LeetCodeSyncEngine:
    """Coordinates account connection, data retrieval, deduplication, storage, and memory engine sync."""

    def __init__(
        self,
        account_service: Optional[AccountService] = None,
        client: Optional[LeetCodeClient] = None,
        sync_limit: int = DEFAULT_SYNC_LIMIT,
    ):
        self.account_service = account_service or AccountService()
        self.client = client or LeetCodeClient()
        self.mapper = LeetCodeMapper()
        self.sync_limit = max(1, int(sync_limit))

    def connect_account(self, username: str) -> AccountConnection:
        """Validate username via public GraphQL endpoint and store account connection metadata."""
        username_clean = (username or "").strip()
        if not username_clean:
            raise ValueError("Username cannot be empty.")

        profile_data = self.client.fetch_user_profile(username_clean)
        if not profile_data:
            # Fallback connection metadata if offline / network issue, or raise validation error
            raise ValueError(f"LeetCode account '{username_clean}' could not be validated. Check username or internet connection.")

        conn = AccountConnection(
            provider="LeetCode",
            username=profile_data["username"],
            display_name=profile_data.get("real_name") or profile_data["username"],
            user_avatar=profile_data.get("user_avatar"),
            status=AccountStatus.CONNECTED,
            connected_at=datetime.now(timezone.utc),
            capabilities=LEETCODE_CAPABILITIES,
            metadata={
                "solved_all": profile_data.get("solved_all", 0),
                "solved_easy": profile_data.get("solved_easy", 0),
                "solved_medium": profile_data.get("solved_medium", 0),
                "solved_hard": profile_data.get("solved_hard", 0),
                "ranking": profile_data.get("ranking"),
            },
        )
        return self.account_service.save_connection(conn)

    def _read_watermark(self, conn: AccountConnection) -> Optional[tuple[float, tuple[int, str]]]:
        """Reconstruct the persisted watermark ordering tuple, or ``None`` if absent.

        Purely local state. This value is never transmitted to LeetCode.
        """
        metadata = conn.metadata or {}
        stored_ts = metadata.get(WATERMARK_KEY_TS)
        stored_id = metadata.get(WATERMARK_KEY_ID)
        if not stored_ts and not stored_id:
            return None
        try:
            ts = datetime.fromisoformat(str(stored_ts)) if stored_ts else None
        except ValueError:
            logger.warning("Ignoring unparseable persisted watermark timestamp: %r", stored_ts)
            return None
        return _record_key(ts, stored_id)

    @staticmethod
    def _write_watermark(conn: AccountConnection, key: tuple[float, tuple[int, str]]) -> None:
        """Store a watermark ordering tuple back onto the connection metadata."""
        conn.metadata[WATERMARK_KEY_TS] = datetime.fromtimestamp(key[0], tz=timezone.utc).isoformat()
        conn.metadata[WATERMARK_KEY_ID] = None
        # Recover the external id text from the numeric sort key where possible.
        numeric = key[1][0]
        if numeric >= 0:
            conn.metadata[WATERMARK_KEY_ID] = f"leetcode_{numeric}"

    def sync(self, service: Any, limit: Optional[int] = None) -> SyncStatus:
        """Synchronize public profile and the recent submission window.

        ``limit`` overrides the engine's configured ``sync_limit`` for this call
        only. It is a local bound on how many records to request; it is not a
        cursor and is never used to page backwards.
        """
        conn = self.account_service.get_connection("LeetCode")
        if not conn or conn.status != AccountStatus.CONNECTED:
            raise ValueError("LeetCode account is not connected.")

        window_limit = max(1, int(limit)) if limit is not None else self.sync_limit

        now = datetime.now(timezone.utc)
        sync_status = SyncStatus(started_at=now, status=SyncState.RUNNING)

        try:
            # 1. Update Profile Metadata.
            # A failed profile fetch is a real defect worth reporting, not a
            # silent skip: submission data may still sync, so the run becomes
            # PARTIAL rather than FAILED.
            profile_data = self.client.fetch_user_profile(conn.username)
            profile_failed = profile_data is None
            if profile_data:
                conn.display_name = profile_data.get("real_name") or conn.username
                conn.user_avatar = profile_data.get("user_avatar") or conn.user_avatar
                conn.metadata.update(
                    {
                        "solved_all": profile_data.get("solved_all", 0),
                        "solved_easy": profile_data.get("solved_easy", 0),
                        "solved_medium": profile_data.get("solved_medium", 0),
                        "solved_hard": profile_data.get("solved_hard", 0),
                        "ranking": profile_data.get("ranking"),
                    }
                )
            else:
                logger.warning("LeetCode profile fetch failed for '%s'; sync will be PARTIAL", conn.username)

            # 2. Fetch the recent accepted-submission window via GraphQL.
            raw_subs: list[LeetCodeSubmissionRaw] = self.client.fetch_user_submissions(
                conn.username, limit=window_limit
            )
            sync_status.records_discovered = len(raw_subs)

            # Normalize once; the ordering tuples are derived from the same
            # records the persistence loop consumes below. Provenance is passed
            # into the mapper so source_account is available during the record's
            # hash computation (provenance must precede hashing to produce
            # account-distinct hashes).
            normalized = [
                self.mapper.to_normalized_record(r, source_account=conn.username)
                for r in raw_subs
            ]
            visible_keys = [_record_key(n.timestamp, n.submission_id) for n in normalized]

            previous_watermark = self._read_watermark(conn)

            added_count = 0
            skipped_count = 0

            for norm in normalized:
                try:
                    problem_slug = norm.problem_id or generate_slug(norm.title)

                    # Ensure problem exists in storage or fetch problem metadata
                    prob = None
                    try:
                        prob = service.get_problem(problem_slug)
                    except ProblemNotFoundError:
                        # Problem not found locally -> fetch problem details from LeetCode
                        raw_prob = self.client.fetch_problem_details(problem_slug)
                        if raw_prob:
                            prob_data = self.mapper.to_normalized_problem(raw_prob)
                            prob = service.add_problem(
                                title=prob_data["title"],
                                slug=prob_data["slug"],
                                difficulty=prob_data["difficulty"],
                                topics=prob_data["topics"],
                                url=prob_data["url"],
                                statement=prob_data.get("statement"),
                            )
                        else:
                            prob = service.add_problem(
                                title=norm.title,
                                slug=problem_slug,
                                difficulty=norm.difficulty,
                                topics=norm.topics,
                                url=norm.url,
                            )

                    # Idempotency guard, evaluated against storage plus whatever
                    # this run has already persisted. service.add_submission()
                    # additionally checks storage by hash, so a re-sync of an
                    # already persisted submission can never create a duplicate.
                    existing_hashes = {
                        s.submission_hash for a in prob.attempts for s in a.submissions if s.submission_hash
                    }
                    existing_ids = {s.id for a in prob.attempts for s in a.submissions}
                    # Map from hash → set of source_accounts that claim it, so a
                    # cross-account hash collision does not cause B's submission to
                    # be skipped against A's record (or vice-versa).
                    hash_accounts: dict[str, set[str | None]] = {}
                    for a in prob.attempts:
                        for s in a.submissions:
                            if s.submission_hash:
                                hash_accounts.setdefault(s.submission_hash, set()).add(s.source_account)

                    sub_id_check = norm.submission_id or ""

                    # A submission is a duplicate only if BOTH its external id
                    # and its hash+account match what is already stored. A hash
                    # that matches A's record but belongs to a different account
                    # is a cross-account collision, not a duplicate.
                    is_duplicate_id = sub_id_check in existing_ids
                    is_duplicate_hash = norm.submission_hash in existing_hashes and (
                        conn.username in hash_accounts.get(norm.submission_hash, set())
                    )

                    if is_duplicate_id or is_duplicate_hash:
                        skipped_count += 1
                        continue

                    # Persist the submission with its external identity intact.
                    # The supported public API returns no source code and no
                    # runtime/memory, so those are persisted as absent rather than
                    # fabricated: an invented snippet would corrupt the canonical
                    # hash and misrepresent the user's history.
                    _, stored = service.add_submission(
                        problem_identifier=prob.slug,
                        code=norm.code,
                        language=norm.language,
                        status=norm.status,
                        runtime_ms=norm.runtime_ms,
                        memory_mb=norm.memory_mb,
                        submitted_at=norm.timestamp,
                        submission_id=norm.submission_id,
                        submission_hash=norm.submission_hash,
                        source_provider="leetcode",
                        source_account=conn.username,
                    )

                    # Account for what this run wrote, so a duplicate appearing
                    # later in the same window counts as skipped, not added.
                    existing_ids.add(stored.id)
                    if norm.submission_hash:
                        existing_hashes.add(norm.submission_hash)
                    added_count += 1

                except Exception as ex:
                    logger.warning("Error processing synced submission item: %s", ex)
                    sync_status.records_failed += 1

            sync_status.records_added = added_count
            sync_status.records_skipped = skipped_count

            # 3. Advance the watermark ONLY once every discovered record has been
            # durably persisted. A single failed record preserves the previous
            # watermark so the next run re-processes the window from a known-good
            # baseline. The watermark never regresses: a record removed upstream
            # must not make us forget what we have already seen.
            watermark = previous_watermark
            if visible_keys and sync_status.records_failed == 0:
                candidate = max(visible_keys)
                if watermark is None or candidate > watermark:
                    watermark = candidate
                    self._write_watermark(conn, watermark)

            # 4. Report the honest coverage contract. The window is bounded by the
            # server; a full count here would be a claim the API cannot support.
            sync_status.details = {
                "coverage": "recent-window",
                "window_limit": window_limit,
                "records_in_window": len(raw_subs),
                "window_truncated": len(raw_subs) >= window_limit,
                "gap_detected": self._gap_detected(visible_keys, previous_watermark),
                "unavailable_fields": list(UNAVAILABLE_FIELDS),
                "profile_fetch_failed": profile_failed,
            }

            sync_status.finished_at = datetime.now(timezone.utc)
            if sync_status.records_failed > 0 or profile_failed:
                sync_status.status = SyncState.PARTIAL
            else:
                sync_status.status = SyncState.SUCCESS

            if profile_failed and not sync_status.error_message:
                sync_status.error_message = "LeetCode profile fetch failed; submission data may be incomplete."

            # 5. Refresh downstream indexes only when the data actually changed.
            # An unchanged window writes nothing, so rebuilding would be pure cost.
            if added_count > 0:
                try:
                    service.memory_engine.index_all(force_rebuild=False)
                except Exception as e_mem:
                    logger.warning("Memory engine index update notice: %s", e_mem)

            # 6. Update Connection Sync Metadata
            conn.last_sync_at = sync_status.finished_at
            conn.last_sync_status = sync_status.status
            conn.last_sync_error = sync_status.error_message
            self.account_service.save_connection(conn)

            return sync_status

        except Exception as e:
            sync_status.status = SyncState.FAILED
            sync_status.error_message = str(e)
            sync_status.finished_at = datetime.now(timezone.utc)

            conn.last_sync_at = sync_status.finished_at
            conn.last_sync_status = SyncState.FAILED
            conn.last_sync_error = str(e)
            self.account_service.save_connection(conn)

            return sync_status

    @staticmethod
    def _gap_detected(
        visible_keys: list[tuple[float, tuple[int, str]]],
        watermark: Optional[tuple[float, tuple[int, str]]],
    ) -> bool:
        """Report whether older submissions may have fallen outside the window.

        The window shows the most recent N submissions. If the OLDEST visible
        record is newer than the newest persisted one, then records strictly
        between the two exist on LeetCode but are no longer reachable through the
        bounded window — a permanent, unrecoverable gap.

        Without a prior watermark (first sync) there is no baseline to compare
        against, so no gap is claimed; ``window_truncated`` carries that signal.
        """
        if watermark is None or not visible_keys:
            return False
        return min(visible_keys) > watermark

    def disconnect_account(self) -> bool:
        """Disconnect LeetCode account metadata while preserving historical CodeMemory data."""
        return self.account_service.remove_connection("LeetCode")
