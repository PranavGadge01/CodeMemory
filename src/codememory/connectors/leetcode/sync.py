"""LeetCode Sync Engine coordinating profile, progress, submission sync, and memory indexing."""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, Optional

from codememory.connectors.account.models import AccountConnection, AccountStatus, SyncState, SyncStatus
from codememory.connectors.account.service import AccountService
from codememory.connectors.leetcode.capabilities import LEETCODE_CAPABILITIES
from codememory.connectors.leetcode.client import LeetCodeClient
from codememory.connectors.leetcode.mapper import LeetCodeMapper
from codememory.connectors.leetcode.models import LeetCodeSubmissionRaw
from codememory.domain.models import generate_slug

logger = logging.getLogger(__name__)


class LeetCodeSyncEngine:
    """Coordinates account connection, data retrieval, deduplication, storage, and memory index sync."""

    def __init__(
        self,
        account_service: Optional[AccountService] = None,
        client: Optional[LeetCodeClient] = None,
    ):
        self.account_service = account_service or AccountService()
        self.client = client or LeetCodeClient()
        self.mapper = LeetCodeMapper()

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

    def sync(self, service: Any) -> SyncStatus:
        """Synchronize public profile and recent submissions, updating domain storage & memory engine."""
        conn = self.account_service.get_connection("LeetCode")
        if not conn or conn.status != AccountStatus.CONNECTED:
            raise ValueError("LeetCode account is not connected.")

        now = datetime.now(timezone.utc)
        sync_status = SyncStatus(started_at=now, status=SyncState.RUNNING)

        try:
            # 1. Update Profile Metadata
            profile_data = self.client.fetch_user_profile(conn.username)
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

            # 2. Fetch Recent Submissions via GraphQL
            raw_subs: list[LeetCodeSubmissionRaw] = self.client.fetch_user_submissions(conn.username, limit=25)
            sync_status.records_discovered = len(raw_subs)

            added_count = 0
            skipped_count = 0

            for sub_raw in raw_subs:
                try:
                    # Map to normalized record
                    norm = self.mapper.to_normalized_record(sub_raw)
                    problem_slug = norm.problem_id or generate_slug(norm.title)

                    # Ensure problem exists in storage or fetch problem metadata
                    prob = None
                    try:
                        prob = service.get_problem(problem_slug)
                    except Exception:
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
                            )

                    # Check deduplication in problem submissions
                    existing_hashes = {
                        s.submission_hash for a in prob.attempts for s in a.submissions if s.submission_hash
                    }
                    existing_ids = {
                        s.id for a in prob.attempts for s in a.submissions
                    }

                    sub_id_check = norm.submission_id or ""

                    if norm.submission_hash in existing_hashes or sub_id_check in existing_ids:
                        skipped_count += 1
                        continue

                    # Add new submission
                    service.add_submission(
                        problem_identifier=prob.slug,
                        code=norm.code or f"# Synced from LeetCode ({norm.status.value})\n# Title: {norm.title}",
                        language=norm.language,
                        status=norm.status,
                        runtime_ms=norm.runtime_ms,
                        memory_mb=norm.memory_mb,
                    )
                    added_count += 1

                except Exception as ex:
                    logger.warning("Error processing synced submission item: %s", ex)
                    sync_status.records_failed += 1

            sync_status.records_added = added_count
            sync_status.records_skipped = skipped_count
            sync_status.status = SyncState.SUCCESS
            sync_status.finished_at = datetime.now(timezone.utc)

            # 3. Update Memory Engine Vector Index Incremental Build
            try:
                service.memory_engine.index_all(force_rebuild=False)
            except Exception as e_mem:
                logger.warning("Memory engine index update notice: %s", e_mem)

            # 4. Update Connection Sync Metadata
            conn.last_sync_at = sync_status.finished_at
            conn.last_sync_status = SyncState.SUCCESS
            conn.last_sync_error = None
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

    def disconnect_account(self) -> bool:
        """Disconnect LeetCode account metadata while preserving historical CodeMemory data."""
        return self.account_service.remove_connection("LeetCode")
