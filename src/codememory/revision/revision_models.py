"""Models for CodeMemory Revision Engine."""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class RevisionWeights(BaseModel):
    """Configurable weights for deterministic revision scoring formula."""

    difficulty_weight: float = 2.0
    failure_weight: float = 3.0
    recency_weight: float = 2.5
    weakness_weight: float = 2.0
    recent_solved_penalty_weight: float = 1.5


class RevisionScoreBreakdown(BaseModel):
    """Detailed scoring breakdown for a problem's revision priority."""

    problem_id: str
    title: str
    slug: str
    difficulty: str
    final_score: float
    difficulty_score: float
    failure_score: float
    recency_score: float
    weakness_score: float
    recent_solved_penalty: float
    days_since_last_activity: int


class RevisionQueueItem(BaseModel):
    """Prioritized problem item in revision queue."""

    problem_id: str
    title: str
    slug: str
    difficulty: str
    priority_score: float
    last_activity_at: datetime
    topics: list[str] = Field(default_factory=list)
    breakdown: RevisionScoreBreakdown
