"""Structured Pydantic models for analytics results."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class AnalyticsOverview(BaseModel):
    """System-wide problem solving overview statistics."""

    total_problems: int = 0
    total_attempts: int = 0
    total_submissions: int = 0
    accepted_problems: int = 0
    unsolved_problems: int = 0
    overall_acceptance_rate_pct: float = 0.0
    avg_attempts_per_solved_problem: float = 0.0
    first_attempt_acceptance_rate_pct: float = 0.0
    repeated_problem_rate_pct: float = 0.0
    avg_solving_time_minutes: float | None = None
    current_streak_days: int = 0
    longest_streak_days: int = 0
    active_days_last_30: int = 0


class TopicStat(BaseModel):
    """Analytics metric breakdown by DSA topic."""

    topic: str
    total_problems: int = 0
    solved_problems: int = 0
    total_attempts: int = 0
    total_submissions: int = 0
    accepted_submissions: int = 0
    acceptance_rate_pct: float = 0.0
    success_rate_pct: float = 0.0


class DifficultyStat(BaseModel):
    """Analytics metric breakdown by problem difficulty."""

    difficulty: str
    total_problems: int = 0
    solved_problems: int = 0
    total_attempts: int = 0
    total_submissions: int = 0
    accepted_submissions: int = 0
    acceptance_rate_pct: float = 0.0


class LanguageStat(BaseModel):
    """Analytics metric breakdown by programming language."""

    language: str
    total_submissions: int = 0
    accepted_submissions: int = 0
    acceptance_rate_pct: float = 0.0
    usage_share_pct: float = 0.0


class AttemptStat(BaseModel):
    """Statistics on attempt distributions and progression."""

    total_attempts: int = 0
    avg_attempts_per_problem: float = 0.0
    single_attempt_solved_count: int = 0
    multiple_attempt_solved_count: int = 0
    max_attempts_single_problem: int = 0
    brute_force_to_optimized_count: int = 0


class ProgressOverTime(BaseModel):
    """Progress metrics aggregated by time bucket (day/week/month)."""

    period: str  # e.g., "2026-09-06" or "2026-W36" or "2026-09"
    problems_solved: int = 0
    total_submissions: int = 0
    accepted_submissions: int = 0


class StruggleProblem(BaseModel):
    """Problem requiring significant attempts or suffering repeated failures."""

    problem_id: str
    title: str
    slug: str
    difficulty: str
    total_attempts: int = 0
    failed_attempts: int = 0
    failed_submissions: int = 0
    status: str
    topics: list[str] = Field(default_factory=list)


class ActivityDay(BaseModel):
    """Daily activity metrics for the activity heatmap."""

    date: str  # ISO date "YYYY-MM-DD"
    submissions: int = 0
    accepted: int = 0
    solved: int = 0
    minutes_active: int = 0


class StreakInfo(BaseModel):
    """Streak statistics computed from activity data."""

    current_streak_days: int = 0
    longest_streak_days: int = 0
    active_days_last_30: int = 0


class TimelineEvent(BaseModel):
    """Single chronological event for the dashboard timeline."""

    id: str
    kind: str  # "solved", "attempted", "learned", "imported"
    title: str
    detail: str
    problem_id: Optional[str] = None
    problem_slug: Optional[str] = None
    language: Optional[str] = None
    occurred_at: datetime


class KnowledgeCluster(BaseModel):
    """A group of related problems sharing a common topic or concept."""

    id: str
    title: str
    description: str
    topic_id: str
    problem_ids: list[str] = Field(default_factory=list)
    mastery_pct: int = 0
