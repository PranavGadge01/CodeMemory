"""UI-friendly product models for the ProductService facade layer."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from codememory.analytics.analytics_models import (
    AnalyticsOverview,
    DifficultyStat,
    LanguageStat,
    ProgressOverTime,
    StruggleProblem,
    TopicStat,
)
from codememory.revision.revision_models import RevisionQueueItem


class ActivityData(BaseModel):
    """Activity data point for dashboard calendar/graph."""

    date: str  # ISO format: YYYY-MM-DD
    problems_solved: int = 0
    total_submissions: int = 0
    accepted_submissions: int = 0


class DashboardData(BaseModel):
    """Aggregated dashboard metrics and activity data."""

    solved_count: int = 0
    submission_count: int = 0
    streak: int = 0
    activity: list[ActivityData] = Field(default_factory=list)
    overview: Optional[AnalyticsOverview] = None


class ProblemView(BaseModel):
    """UI-friendly problem representation."""

    id: str
    title: str
    slug: str
    difficulty: str
    topics: list[str] = Field(default_factory=list)
    platform: str = "LeetCode"
    url: Optional[str] = None

    # Status fields
    solved: bool = False
    last_attempted_at: Optional[datetime] = None
    last_solved_at: Optional[datetime] = None

    # Metadata
    attempt_count: int = 0
    submission_count: int = 0
    languages: list[str] = Field(default_factory=list)


class SubmissionView(BaseModel):
    """UI-friendly submission representation."""

    id: str
    problem_id: str
    problem_title: str
    code: str
    language: str
    status: str
    runtime_ms: Optional[float] = None
    memory_mb: Optional[float] = None
    submitted_at: datetime
    attempt_number: int = 1
    error_message: Optional[str] = None


class AnalyticsData(BaseModel):
    """Complete analytics data wrapper."""

    overview: AnalyticsOverview = Field(default_factory=AnalyticsOverview)
    by_topic: list[TopicStat] = Field(default_factory=list)
    by_difficulty: list[DifficultyStat] = Field(default_factory=list)
    by_language: list[LanguageStat] = Field(default_factory=list)
    progress_over_time: list[ProgressOverTime] = Field(default_factory=list)
    struggle_problems: list[StruggleProblem] = Field(default_factory=list)


class KnowledgeData(BaseModel):
    """Knowledge and revision insights."""

    weak_topics: list[dict] = Field(default_factory=list)
    high_failure_topics: list[dict] = Field(default_factory=list)
    repeated_tle_problems: list[str] = Field(default_factory=list)
    repeated_wa_problems: list[str] = Field(default_factory=list)
    high_attempt_problems: list[dict] = Field(default_factory=list)
    improvement_patterns: list[dict] = Field(default_factory=list)
    revision_queue: list[RevisionQueueItem] = Field(default_factory=list)
