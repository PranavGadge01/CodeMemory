"""LeetCode connector implementing standard platform synchronization interface."""

from typing import Any, List, Optional, Union
from pathlib import Path

from codememory.connectors.base import BaseConnector, RawExternalSubmission
from codememory.connectors.leetcode.client import LeetCodeClient
from codememory.connectors.leetcode.importer import LeetCodeImporter
from codememory.domain.models import generate_slug
from codememory.ingestion.importer import ImportSummary
from codememory.storage.composite_repository import CompositeStorage


class LeetCodeConnector(BaseConnector):
    """Platform connector for LeetCode integrating GraphQL API and file imports."""

    def __init__(self, api_session_cookie: Optional[str] = None, storage: Optional[CompositeStorage] = None):
        self.api_session_cookie = api_session_cookie
        self.client = LeetCodeClient(session_cookie=api_session_cookie)
        self.storage = storage
        self.importer = LeetCodeImporter(storage=storage) if storage else None

    def fetch_user_submissions(self, username: str, limit: int = 100) -> List[RawExternalSubmission]:
        """Fetch recent submissions from LeetCode GraphQL endpoint.

        Returns raw transport records only. Conversion to the CodeMemory domain
        happens in :meth:`BaseConnector.normalize_submission`, which every caller
        funnels through.
        """
        raw_items = self.client.fetch_user_submissions(username, limit=limit)
        results: List[RawExternalSubmission] = []

        for item in raw_items:
            external_sub_id = item.submission_id or item.id
            slug = item.title_slug or generate_slug(item.title)
            results.append(
                RawExternalSubmission(
                    external_id=f"leetcode_{external_sub_id}" if external_sub_id else f"leetcode_unassigned_{username}",
                    problem_title=item.title,
                    problem_slug=slug,
                    difficulty=item.difficulty,
                    topics=item.topics,
                    language=item.language,
                    code=item.code,
                    status=item.status,
                    runtime=item.runtime,
                    memory=item.memory,
                    timestamp=str(item.timestamp) if item.timestamp is not None else None,
                    url=item.url or f"https://leetcode.com/problems/{slug}/",
                )
            )
        return results

    def fetch_problem_details(self, problem_slug: str) -> Optional[dict[str, Any]]:
        """Fetch problem details from LeetCode API."""
        prob_raw = self.client.fetch_problem_details(problem_slug)
        if not prob_raw:
            return {
                "title": problem_slug.replace("-", " ").title(),
                "slug": problem_slug,
                "platform": "LeetCode",
                "url": f"https://leetcode.com/problems/{problem_slug}/",
            }
        res = prob_raw.model_dump()
        res["platform"] = "LeetCode"
        res["slug"] = prob_raw.title_slug
        return res

    def import_dataset(self, file_path: Union[str, Path]) -> ImportSummary:
        """Import LeetCode dataset file idempotently."""
        if not self.importer:
            raise ValueError("CompositeStorage instance required for dataset importing.")
        return self.importer.import_file(file_path)
