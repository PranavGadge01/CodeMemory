"""Authenticated LeetCode client for full-history sync using session cookies."""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from codememory.connectors.leetcode.client import LeetCodeClient
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
from codememory.connectors.leetcode.vault import CredentialVault

logger = logging.getLogger(__name__)

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"


class AuthenticatedLeetCodeClient(LeetCodeClient):
    """
    Authenticated LeetCode GraphQL client that uses session cookies for
    accessing full submission history and private data.

    Extends the base LeetCodeClient but adds authentication headers for
    accessing the full submissionList GraphQL query.
    """

    def __init__(
        self,
        session_cookie: Optional[str] = None,
        csrf_token: Optional[str] = None,
        *,
        connect_timeout: float = 10.0,
        read_timeout: float = 30.0,
        max_retries: int = 3,
        backoff_base: float = 0.5,
        backoff_max: float = 8.0,
        rate_limit_max_wait: float = 60.0,
        opener: Optional[Any] = None,
        sleep_fn: callable = time.sleep,
        random_fn: callable = lambda a, b: __import__('random').uniform(a, b),
    ) -> None:
        """
        Initialize authenticated LeetCode client.

        Args:
            session_cookie: LEETCODE_SESSION cookie value
            csrf_token: csrftoken cookie value
            Other parameters inherited from LeetCodeClient
        """
        # Initialize parent class (but we override _headers so session_cookie won't be used there)
        super().__init__(
            session_cookie=None,  # We'll handle credentials in our own _headers
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
            max_retries=max_retries,
            backoff_base=backoff_base,
            backoff_max=backoff_max,
            rate_limit_max_wait=rate_limit_max_wait,
            opener=opener,
            sleep_fn=sleep_fn,
            random_fn=random_fn,
        )

        # Store credentials separately for header construction - AFTER parent init
        self.session_cookie = session_cookie
        self.csrf_token = csrf_token

        # Validate that we have credentials
        if not self.session_cookie or not self.csrf_token:
            raise ValueError("Both session_cookie and csrf_token are required for authenticated client")

    def _headers(self) -> Dict[str, str]:
        """
        Construct HTTP headers for authenticated LeetCode GraphQL request.

        Includes authentication cookies and headers required for private GraphQL queries.
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

        # Add authentication headers
        if self.session_cookie and self.csrf_token:
            headers["Cookie"] = f"LEETCODE_SESSION={self.session_cookie}; csrftoken={self.csrf_token}"
            headers["x-csrftoken"] = self.csrf_token

        return headers

    def validate_session(self) -> bool:
        """Check the stored session with a lightweight authenticated request.

        A single history item is sufficient to distinguish an accepted session
        from rejected credentials without importing or persisting any data.
        """
        self.fetch_submissions_page(username="", limit=1, offset=0)
        return True

    def fetch_submissions_page(
        self,
        username: str,
        limit: int = 100,
        offset: int = 0,
        last_key: Optional[str] = None
    ) -> tuple[List[LeetCodeSubmissionRaw], bool, Optional[str]]:
        """
        Fetch a single page of submissions for a user using GraphQL query.

        Uses the submissionList query with pagination via offset and lastKey.

        Args:
            username: LeetCode username
            limit: Number of submissions to fetch per page (max 100)
            offset: Offset for pagination
            last_key: Pagination key to resume from (for checkpoint resume)

        Returns:
            Tuple of (submissions_list, has_next, next_last_key)

        Raises:
            LeetCodeError: On authentication failure or other errors
        """
        if limit > 100:
            limit = 100  # GraphQL API limit

        # The authenticated session identifies the current user. The current
        # schema returns page entries under ``submissions``.
        query = """
        query submissionList($limit: Int!, $offset: Int!, $lastKey: String) {
            submissionList(limit: $limit, offset: $offset, lastKey: $lastKey) {
                submissions {
                    id
                    title
                    titleSlug
                    timestamp
                    statusDisplay
                    lang
                    __typename
                }
                hasNext
                lastKey
            }
        }
        """

        variables = {
            "limit": limit,
            "offset": offset,
            "lastKey": last_key
        }

        try:
            result = self.execute_query(query, variables)

            if result is None:
                logger.error("Failed to fetch submission list - received None response")
                raise LeetCodeError(self.last_error or "LeetCode submission-list request failed")

            data = self._graphql_data(result)
            if not data:
                raise LeetCodeError(self.last_error or "No data in submission-list response")

            submission_list_data = data.get("submissionList")
            if not isinstance(submission_list_data, dict):
                raise LeetCodeError("LeetCode returned no usable submissionList object")

            raw_submissions = submission_list_data.get("submissions")
            if not isinstance(raw_submissions, list):
                raise LeetCodeError("LeetCode returned no usable submissions list")

            # Process submissions from this page
            page_submissions = []
            for index, item in enumerate(raw_submissions):
                if not isinstance(item, dict):
                    logger.warning(f"Skipping malformed submission at index {index} (not an object)")
                    continue
                try:
                    submission = LeetCodeSubmissionRaw(
                        id=item.get("id"),
                        submission_id=item.get("id"),
                        title=item.get("title") or "",
                        title_slug=item.get("titleSlug"),
                        # Handle missing language gracefully
                        language=item.get("lang") or "Unknown",
                        status=item.get("statusDisplay") or "Unknown",
                        timestamp=item.get("timestamp"),
                    )
                    page_submissions.append(submission)
                except (TypeError, ValueError) as exc:
                    logger.warning(f"Skipping malformed LeetCode submission at index {index}: {exc}")
                    continue

            # Check pagination info
            has_next = submission_list_data.get("hasNext", False)
            next_last_key = submission_list_data.get("lastKey")

            logger.info(f"Fetched {len(page_submissions)} submissions from page: offset={offset}, limit={limit}, lastKey={last_key}")
            return page_submissions, has_next, next_last_key

        except Exception as e:
            logger.error(f"Error fetching submission page: {e}")
            raise

    def fetch_all_submissions_paginated(
        self,
        username: str,
        limit: int = 100,
        delay_between_requests: float = 1.5,
        last_key: Optional[str] = None
    ) -> List[LeetCodeSubmissionRaw]:
        """
        Fetch all submissions for a user using paginated GraphQL queries.

        Uses the submissionList query with pagination via offset and lastKey.

        Args:
            username: LeetCode username
            limit: Number of submissions to fetch per page (max 100)
            delay_between_requests: Delay in seconds between paginated requests
            last_key: Pagination key to resume from (for checkpoint resume)

        Returns:
            List of LeetCodeSubmissionRaw objects

        Raises:
            LeetCodeError: On authentication failure or other errors
        """
        if limit > 100:
            limit = 100  # GraphQL API limit

        all_submissions = []
        offset = 0
        has_next = True
        # Use provided last_key for resume, or start from beginning if None
        current_last_key = last_key

        while has_next:
            page_submissions, has_next, current_last_key = self.fetch_submissions_page(
                username=username,
                limit=limit,
                offset=offset,
                last_key=current_last_key
            )

            all_submissions.extend(page_submissions)
            logger.info(f"Fetched {len(page_submissions)} submissions from page (total: {len(all_submissions)})")

            # Prepare for next page
            offset += limit

            # Rate limiting - delay between requests
            if has_next:  # Only delay if we're going to make another request
                time.sleep(delay_between_requests)

        logger.info(f"Completed paginated fetch: {len(all_submissions)} total submissions")
        return all_submissions

    def fetch_submission_code(self, submission_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch detailed information for a specific submission including source code.

        Uses the submissionDetails query to get full submission details.

        Args:
            submission_id: LeetCode submission ID

        Returns:
            Dictionary with submission details or None if failed

        Raises:
            LeetCodeError: On query failure
        """
        query = """
        query submissionDetails($submissionId: Int!) {
            submissionDetails(submissionId: $submissionId) {
                code
                runtime
                memory
                timestamp
                statusCode
                lang {
                    name
                    verboseName
                }
                question {
                    questionId
                    title
                    titleSlug
                }
            }
        }
        """

        try:
            numeric_submission_id = int(submission_id)
        except (TypeError, ValueError):
            logger.error("Invalid submission ID for detail lookup")
            return None
        variables = {"submissionId": numeric_submission_id}

        try:
            result = self.execute_query(query, variables)
            if result is None:
                logger.error(f"Failed to fetch submission detail for {submission_id}")
                return None

            data = self._graphql_data(result)
            if not data:
                logger.error(f"No data in submission detail response for {submission_id}")
                return None

            submission_detail = data.get("submissionDetails")
            if not submission_detail:
                logger.error(f"No submissionDetails in response for {submission_id}")
                return None

            language = submission_detail.get("lang")
            if isinstance(language, dict):
                language = language.get("verboseName") or language.get("name")
            question = submission_detail.get("question")
            if not isinstance(question, dict):
                question = {}

            # Normalize the response to match our expected format
            normalized = {
                "submission_id": str(submission_id),
                "code": submission_detail.get("code"),
                "language": language,
                "runtime": submission_detail.get("runtime"),
                "memory": submission_detail.get("memory"),
                "status": submission_detail.get("statusCode"),
                "timestamp": submission_detail.get("timestamp"),
                "question_id": question.get("questionId"),
                "title": question.get("title"),
                "title_slug": question.get("titleSlug"),
            }

            return normalized

        except Exception as e:
            logger.error(f"Error fetching submission code for {submission_id}: {e}")
            return None

    # Override execute_query to ensure we don't log sensitive headers
    def execute_query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Execute a GraphQL POST, ensuring credentials are not logged."""
        try:
            # The parent request path uses this instance's overridden _headers;
            # credentials are never included in request logs.
            return super().execute_query(query, variables)
        except Exception as e:
            # Ensure we don't leak credentials in error messages
            error_str = str(e)
            if "LEETCODE_SESSION" in error_str or "csrftoken" in error_str:
                logger.warning("Attempted to leak credentials in error message - sanitizing")
                # Re-raise with sanitized message
                raise LeetCodeError("Request failed (credentials removed from error message)") from e
            raise
