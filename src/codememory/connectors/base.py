"""Abstract connector interface for external coding platforms (LeetCode, HackerRank, Codeforces)."""

from abc import ABC, abstractmethod
from typing import Any, List, Optional
from pydantic import BaseModel, Field
from codememory.domain.import_schema import NormalizedSubmissionRecord


class RawExternalSubmission(BaseModel):
    """Raw submission data structure returned by external connectors."""

    external_id: str
    problem_title: str
    problem_slug: str
    difficulty: Optional[str] = None
    topics: List[str] = Field(default_factory=list)
    language: str
    code: str
    status: str
    runtime: Optional[str] = None
    memory: Optional[str] = None
    timestamp: Optional[str] = None
    url: Optional[str] = None


class BaseConnector(ABC):
    """Abstract base connector establishing standard interfaces for platform data synchronization."""

    @abstractmethod
    def fetch_user_submissions(self, username: str, limit: int = 50) -> List[RawExternalSubmission]:
        """Fetch raw user submissions from external platform."""
        pass

    @abstractmethod
    def fetch_problem_details(self, problem_slug: str) -> Optional[dict[str, Any]]:
        """Fetch problem statement and metadata from external platform."""
        pass

    def normalize_submission(self, raw: RawExternalSubmission) -> NormalizedSubmissionRecord:
        """Convert raw external submission into CodeMemory's normalized import schema."""
        return NormalizedSubmissionRecord(
            problem_id=raw.problem_slug or None,
            title=raw.problem_title,
            difficulty=raw.difficulty,
            topics=raw.topics,
            url=raw.url,
            language=raw.language,
            code=raw.code,
            timestamp=raw.timestamp,
            status=raw.status,
            runtime=raw.runtime,
            memory=raw.memory,
            submission_id=raw.external_id,
        )
