"""Authenticated LeetCode sync orchestrator for full-history synchronization."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

from codememory.connectors.account.models import AccountConnection, AccountStatus, SyncState, SyncStatus
from codememory.connectors.account.service import AccountService
from codememory.connectors.leetcode.authenticated_client import AuthenticatedLeetCodeClient
from codememory.connectors.leetcode.errors import LeetCodeError
from codememory.connectors.leetcode.mapper import LeetCodeMapper
from codememory.connectors.leetcode.vault import CredentialVault
from codememory.domain.enums import SubmissionStatus
from codememory.domain.exceptions import ProblemNotFoundError
from codememory.domain.models import generate_slug

logger = logging.getLogger(__name__)


class AuthenticatedSyncOrchestrator:
    """
    Orchestrates authenticated full-history LeetCode synchronization.

    Coordinates credential retrieval, authenticated API calls, submission processing,
    deduplication, and storage using existing CodeMemory services and repositories.
    """

    def __init__(
        self,
        account_service: Optional[AccountService] = None,
        credential_vault: Optional[CredentialVault] = None,
        rate_limit_delay: float = 1.5,
        account_identifier: str = "default",
    ):
        """
        Initialize the authenticated sync orchestrator.

        Args:
            account service: Service for managing account connections
            credential_vault: Vault for storing/retrieving encrypted credentials
            rate_limit_delay: Delay between paginated requests in seconds
            account_identifier: Identifier for the account (used to isolate credentials)
        """
        self._account_service = account_service or AccountService()
        self._credential_vault = credential_vault or CredentialVault(account_identifier=account_identifier)
        self._rate_limit_delay = rate_limit_delay
        self._mapper = LeetCodeMapper()

        # Statistics tracking
        self.stats = {
            "records_discovered": 0,
            "records_added": 0,
            "records_skipped": 0,
            "records_failed": 0,
            "code_fetched": 0,
            "code_failed": 0,
            "started_at": None,
            "finished_at": None,
            "status": SyncState.IDLE,
            "error_message": None,
        }

    def sync_full_history(self, service: Any, username: Optional[str] = None) -> SyncStatus:
        """
        Perform authenticated full-history sync for LeetCode submissions.

        Args:
            service: CodeMemory service instance for problem/submission storage
            username: Optional username (if not provided, will use connected account)

        Returns:
            SyncStatus object with sync results
        """
        # Reset statistics
        self._reset_stats()
        self.stats["started_at"] = datetime.now(timezone.utc)
        self.stats["status"] = SyncState.RUNNING

        logger.info("Starting authenticated LeetCode full-history sync")

        try:
            # Step 1: Retrieve credentials from vault
            session, csrf_token = self._credential_vault.retrieve()
            if not session or not csrf_token:
                raise ValueError("No authenticated credentials found. Please store credentials first.")

            logger.info("Retrieved credentials from vault")

            # Step 2: Validate credentials format
            if not self._credential_vault.validate(session, csrf_token):
                raise ValueError("Stored credentials appear to be invalid")

            # Step 3: Initialize authenticated client
            client = AuthenticatedLeetCodeClient(
                session_cookie=session,
                csrf_token=csrf_token,
                sleep_fn=time.sleep
            )

            # Step 4: Determine username to sync
            if not username:
                # Get username from connected account
                conn = self._account_service.get_connection("LeetCode")
                if not conn or conn.status != AccountStatus.CONNECTED:
                    raise ValueError("No connected LeetCode account found")
                username = conn.username
                logger.info(f"Using username from connected account: {username}")
            else:
                logger.info(f"Using provided username: {username}")

            # Step 4.5: Load checkpoint for resume capability
            checkpoint_offset = 0
            checkpoint_username = None
            conn = self._account_service.get_connection("LeetCode")
            if conn:
                checkpoint_offset, checkpoint_username = self.load_checkpoint(conn)
                if checkpoint_offset > 0:
                    logger.info(f"Resuming sync from checkpoint offset: {checkpoint_offset} for user {checkpoint_username}")
                else:
                    logger.info("No checkpoint found, starting from beginning")

            # Step 5: Fetch submissions page by page with checkpointing
            logger.info(f"Fetching all submissions for user: {username} starting from offset: {checkpoint_offset}")

            # Initialize pagination variables
            offset = checkpoint_offset
            has_next = True

            # Process pages one at a time with checkpointing
            while has_next:
                # Fetch one page of submissions
                page_submissions, has_next, _ = client.fetch_submissions_page(
                    username=username,
                    limit=100,
                    offset=offset,
                )

                logger.info(f"Fetched {len(page_submissions)} submissions from page (offset={offset})")

                # Process all submissions from this page
                for index, raw_submission in enumerate(page_submissions):
                    logger.debug(f"Processing submission {index+1}/{len(page_submissions)}: {raw_submission.id}")
                    self.stats["records_discovered"] += 1

                    try:
                        # Normalize through existing mapper
                        normalized_record = self._mapper.to_normalized_record(
                            raw_submission,
                            source_account=username
                        )

                        # Check if this is an accepted submission to fetch code
                        if normalized_record.status == SubmissionStatus.ACCEPTED:
                            code_data = client.fetch_submission_code(raw_submission.id)
                            if code_data and code_data.get("code"):
                                normalized_record.code = code_data["code"]
                                # Update other fields if available
                                if code_data.get("language"):
                                    normalized_record.language = code_data["language"]
                                if code_data.get("runtime"):
                                    normalized_record.runtime_ms = code_data["runtime"]
                                if code_data.get("memory"):
                                    normalized_record.memory_mb = code_data["memory"]
                                # Recompute hash with the updated code
                                from codememory.domain.models import compute_submission_hash
                                normalized_record.submission_hash = compute_submission_hash(
                                    problem_title=normalized_record.problem_id or normalized_record.title,
                                    language=normalized_record.language,
                                    code=normalized_record.code,
                                    submitted_at=normalized_record.timestamp,
                                    status=normalized_record.status.value,
                                    source_account=username,
                                )
                                self.stats["code_fetched"] += 1
                                logger.debug(f"Fetched code for submission {raw_submission.id}")
                            else:
                                self.stats["code_failed"] += 1
                                logger.warning(f"Failed to fetch code for accepted submission {raw_submission.id}")

                        # Store submission using existing service logic
                        # This will handle deduplication via submission hash and external ID
                        try:
                            problem_slug = normalized_record.problem_id or generate_slug(normalized_record.title)

                            # Ensure problem exists
                            try:
                                problem = service.get_problem(problem_slug)
                            except ProblemNotFoundError:
                                # Fetch problem details from LeetCode (using public API since we don't have
                                # question details in authenticated client yet - could extend later)
                                from codememory.connectors.leetcode.client import LeetCodeClient
                                public_client = LeetCodeClient()
                                raw_problem = public_client.fetch_problem_details(problem_slug)
                                if raw_problem:
                                    problem_data = self._mapper.to_normalized_problem(raw_problem)
                                    problem = service.add_problem(
                                        title=problem_data["title"],
                                        slug=problem_data["slug"],
                                        difficulty=problem_data["difficulty"],
                                        topics=problem_data["topics"],
                                        url=problem_data["url"],
                                        statement=problem_data.get("statement"),
                                    )
                                else:
                                    problem = service.add_problem(
                                        title=normalized_record.title,
                                        slug=problem_slug,
                                        difficulty=normalized_record.difficulty,
                                        topics=normalized_record.topics,
                                        url=normalized_record.url,
                                    )

                            # Check for duplicate
                            is_duplicate = False
                            if normalized_record.submission_hash:
                                existing_sub = service.storage.get_by_hash(normalized_record.submission_hash)
                                if existing_sub and (existing_sub.source_account == username or existing_sub.source_account is None):
                                    if (existing_sub.code or "") == (normalized_record.code or ""):
                                        is_duplicate = True
                            if not is_duplicate and normalized_record.submission_id:
                                existing_by_id = service.get_submission(normalized_record.submission_id)
                                if existing_by_id and (existing_by_id.source_account == username or existing_by_id.source_account is None):
                                    if (existing_by_id.code or "") == (normalized_record.code or ""):
                                        is_duplicate = True

                            if is_duplicate:
                                self.stats["records_skipped"] += 1
                                logger.debug(f"Skipped duplicate submission {raw_submission.id}")
                                continue

                            # Add submission - this handles deduplication internally
                            _, stored_submission = service.add_submission(
                                problem_identifier=problem.slug,
                                code=normalized_record.code,
                                language=normalized_record.language,
                                status=normalized_record.status,
                                runtime_ms=normalized_record.runtime_ms,
                                memory_mb=normalized_record.memory_mb,
                                submitted_at=normalized_record.timestamp,
                                submission_id=normalized_record.submission_id,
                                submission_hash=normalized_record.submission_hash,
                                source_provider="leetcode",
                                source_account=normalized_record.source_account,
                            )

                            self.stats["records_added"] += 1
                            logger.debug(f"Added submission {raw_submission.id}")

                        except Exception as storage_error:
                            logger.warning(f"Failed to store submission {raw_submission.id}: {storage_error}")
                            self.stats["records_failed"] += 1

                    except Exception as processing_error:
                        logger.warning(f"Error processing submission {raw_submission.id}: {processing_error}")
                        self.stats["records_failed"] += 1

                # After successfully processing the page, save checkpoint
                # using current offset as the resume point for offset-based pagination
                self.save_checkpoint(conn, str(offset + 100), username)

                # Prepare for next page
                offset += 100

                # Rate limiting - delay between requests
                if has_next:  # Only delay if we're going to make another request
                    time.sleep(self._rate_limit_delay)

            logger.info(f"Completed paginated fetch: {self.stats['records_discovered']} total submissions")

            # Step 7: Finalize statistics
            self.stats["finished_at"] = datetime.now(timezone.utc)

            # Clear checkpoint on successful completion (no failures)
            if conn and self.stats["records_failed"] == 0:
                self.clear_checkpoint(conn)
                logger.info("Cleared checkpoint after successful sync completion")

            # Determine final status
            if self.stats["records_failed"] > 0:
                if self.stats["records_added"] == 0 and self.stats["records_discovered"] > 0:
                    self.stats["status"] = SyncState.FAILED
                else:
                    self.stats["status"] = SyncState.PARTIAL
            else:
                self.stats["status"] = SyncState.SUCCESS

            if self.stats["records_failed"] > 0:
                self.stats["error_message"] = f"{self.stats['records_failed']} submissions failed to process"

            logger.info(
                f"Authenticated sync completed: {self.stats['records_added']} added, "
                f"{self.stats['records_skipped']} skipped, {self.stats['records_failed']} failed"
            )

            return self._to_sync_status()

        except Exception as e:
            logger.error(f"Authenticated sync failed: {e}")
            self.stats["finished_at"] = datetime.now(timezone.utc)
            self.stats["status"] = SyncState.FAILED
            self.stats["error_message"] = str(e)
            return self._to_sync_status()

    def _reset_stats(self) -> None:
        """Reset all statistics to initial values."""
        self.stats = {
            "records_discovered": 0,
            "records_added": 0,
            "records_skipped": 0,
            "records_failed": 0,
            "code_fetched": 0,
            "code_failed": 0,
            "started_at": None,
            "finished_at": None,
            "status": SyncState.IDLE,
            "error_message": None,
        }

    def _to_sync_status(self) -> SyncStatus:
        """Convert internal stats to SyncStatus object."""
        return SyncStatus(
            started_at=self.stats["started_at"] or datetime.now(timezone.utc),
            finished_at=self.stats["finished_at"],
            status=self.stats["status"],
            records_discovered=self.stats["records_discovered"],
            records_added=self.stats["records_added"],
            records_skipped=self.stats["records_skipped"],
            records_failed=self.stats["records_failed"],
            error_message=self.stats["error_message"],
            details={
                "code_fetched": self.stats["code_fetched"],
                "code_failed": self.stats["code_failed"],
                "sync_type": "authenticated_full_history",
            }
        )

    # Checkpointing methods - using existing account metadata structure
    def _get_checkpoint_key(self) -> str:
        """Get the metadata key for storing checkpoint."""
        return "auth_sync_last_key"

    def _get_checkpoint_username_key(self) -> str:
        """Get the metadata key for storing checkpoint username."""
        return "auth_sync_last_username"

    def save_checkpoint(self, conn: AccountConnection, last_key: Optional[str], username: str) -> None:
        """
        Save pagination checkpoint to account connection metadata.

        Args:
            conn: Account connection to store checkpoint in
            last_key: Last pagination key from LeetCode response
            username: Username associated with this checkpoint
        """
        if last_key is not None:
            conn.metadata[self._get_checkpoint_key()] = last_key
            conn.metadata[self._get_checkpoint_username_key()] = username
            logger.debug(f"Saved checkpoint for user {username}: {last_key}")
        else:
            # Clear checkpoint if None
            conn.metadata.pop(self._get_checkpoint_key(), None)
            conn.metadata.pop(self._get_checkpoint_username_key(), None)
        if self._account_service:
            self._account_service.save_connection(conn)

    def load_checkpoint(self, conn: AccountConnection) -> tuple[int, Optional[str]]:
        """
        Load pagination checkpoint from account connection metadata.

        Args:
            conn: Account connection to load checkpoint from

        Returns:
            Tuple of (offset, username) or (0, None) if no checkpoint
        """
        checkpoint_str = conn.metadata.get(self._get_checkpoint_key())
        username = conn.metadata.get(self._get_checkpoint_username_key())

        # Validate that username matches current connected account (if any)
        current_conn = self._account_service.get_connection("LeetCode")
        if username and current_conn and current_conn.username != username:
            logger.warning(f"Checkpoint username {username} doesn't match current account {current_conn.username if current_conn else 'None'}")
            return 0, None

        if checkpoint_str is not None:
            try:
                return int(checkpoint_str), username
            except (TypeError, ValueError):
                logger.warning(f"Invalid checkpoint offset '{checkpoint_str}', starting from beginning")
                return 0, None
        return 0, None

    def clear_checkpoint(self, conn: AccountConnection) -> None:
        """Clear pagination checkpoint from account connection metadata."""
        conn.metadata.pop(self._get_checkpoint_key(), None)
        conn.metadata.pop(self._get_checkpoint_username_key(), None)
        if self._account_service:
            self._account_service.save_connection(conn)
        logger.debug("Cleared authentication sync checkpoint")