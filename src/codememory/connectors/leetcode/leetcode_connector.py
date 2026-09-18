"""LeetCode connector implementing standard platform synchronization interface."""

from typing import Any, List, Optional, Union
from pathlib import Path

from codememory.connectors.base import BaseConnector, RawExternalSubmission
from codememory.connectors.leetcode.client import LeetCodeClient
from codememory.connectors.leetcode.importer import LeetCodeImporter
from codememory.connectors.leetcode.mapper import LeetCodeMapper
from codememory.connectors.leetcode.parser import LeetCodeParser
from codememory.domain.import_schema import NormalizedSubmissionRecord
from codememory.ingestion.importer import ImportSummary
from codememory.storage.composite_repository import CompositeStorage


class LeetCodeConnector(BaseConnector):
    """Platform connector for LeetCode integrating GraphQL API and file imports."""

    def __init__(self, api_session_cookie: Optional[str] = None, storage: Optional[CompositeStorage] = None):
        self.api_session_cookie = api_session_cookie
        self.client = LeetCodeClient(session_cookie=api_session_cookie)
        self.storage = storage
        self.importer = LeetCodeImporter(storage=storage) if storage else None

    def fetch_user_submissions(self, username: str, limit: int = 50) -> List[RawExternalSubmission]:
        """Fetch recent submissions from LeetCode GraphQL endpoint."""
        raw_items = self.client.fetch_user_submissions(username, limit=limit)
        results: List[RawExternalSubmission] = []

        for item in raw_items:
            norm_rec = LeetCodeMapper.to_normalized_record(item)
            results.append(
                RawExternalSubmission(
                    external_id=norm_rec.submission_id or f"leetcode_{item.id}",
                    problem_title=norm_rec.title,
                    problem_slug=item.title_slug or norm_rec.title.lower().replace(" ", "-"),
                    difficulty=norm_rec.difficulty,
                    topics=norm_rec.topics,
                    language=norm_rec.language,
                    code=norm_rec.code,
                    status=norm_rec.status.value,
                    runtime=norm_rec.runtime,
                    memory=norm_rec.memory,
                    timestamp=norm_rec.timestamp,
                    url=norm_rec.url,
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
