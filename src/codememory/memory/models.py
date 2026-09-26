"""Unified domain models for CodeMemory Personal Memory Engine."""

from datetime import datetime, timezone
from enum import Enum
import hashlib
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    """Categorization of CodeMemory memory items."""

    PROBLEM = "Problem"
    ATTEMPT = "Attempt"
    SUBMISSION = "Submission"
    MISTAKE = "Mistake"
    PATTERN = "Pattern"
    NOTE = "Note"
    AI_ANALYSIS = "AI Analysis"
    EVOLUTION = "Solution Evolution"


def compute_content_hash(content: str) -> str:
    """Compute deterministic SHA-256 hash for document content."""
    return hashlib.sha256((content or "").strip().encode("utf-8")).hexdigest()


class MemoryDocument(BaseModel):
    """Unified memory item retaining full provenance back to source records."""

    memory_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    memory_type: MemoryType
    problem_id: str
    title: str
    content: str
    topics: List[str] = Field(default_factory=list)
    patterns: List[str] = Field(default_factory=list)
    difficulty: str = "Unknown"
    platform: str = "LeetCode"
    status: str = "Unknown"
    language: str = "python"
    attempt_number: Optional[int] = None
    submission_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "System"
    source_reference: Dict[str, Any] = Field(default_factory=dict)
    content_hash: str = ""
    source_provider: str | None = None
    source_account: str | None = None

    def model_post_init(self, __context: Any) -> None:
        if not self.content_hash and self.content:
            self.content_hash = compute_content_hash(f"{self.memory_type}:{self.title}:{self.content}")


class MemoryResult(BaseModel):
    """Ranked search result from HybridRetriever."""

    memory_id: str
    score: float
    memory_type: MemoryType
    problem_id: str
    title: str
    snippet: str
    content: str
    topics: List[str] = Field(default_factory=list)
    patterns: List[str] = Field(default_factory=list)
    difficulty: str = "Unknown"
    status: str = "Unknown"
    source: str = "System"
    source_reference: Dict[str, Any] = Field(default_factory=dict)
    explanation: Optional[str] = None
    source_provider: str | None = None
    source_account: str | None = None


class SimilarProblemResult(BaseModel):
    """Structured result for problem similarity recommendations."""

    problem_id: str
    title: str
    difficulty: str
    similarity_score: float
    shared_topics: List[str] = Field(default_factory=list)
    shared_patterns: List[str] = Field(default_factory=list)
    explanation: str
