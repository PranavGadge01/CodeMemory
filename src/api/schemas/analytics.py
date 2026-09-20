from typing import List, Optional
from api.schemas.common import BaseCamelModel

class AnalyticsOverviewOut(BaseCamelModel):
    total_problems: int
    total_attempts: int
    total_submissions: int
    accepted_problems: int
    unsolved_problems: int
    overall_acceptance_rate_pct: float
    avg_attempts_per_solved_problem: float
    first_attempt_acceptance_rate_pct: float
    repeated_problem_rate_pct: float
    avg_solving_time_minutes: Optional[float] = None
    current_streak_days: int = 0
    longest_streak_days: int = 0
    active_days_last_30: int = 0

class TopicStatOut(BaseCamelModel):
    topic: str
    total_problems: int
    solved_problems: int
    total_attempts: int
    total_submissions: int
    accepted_submissions: int
    acceptance_rate_pct: float
    success_rate_pct: float

class DifficultyStatOut(BaseCamelModel):
    difficulty: str
    total_problems: int
    solved_problems: int
    total_attempts: int
    total_submissions: int
    accepted_submissions: int
    acceptance_rate_pct: float

class LanguageStatOut(BaseCamelModel):
    language: str
    total_submissions: int
    accepted_submissions: int
    acceptance_rate_pct: float
    usage_share_pct: float

class ProgressOverTimeOut(BaseCamelModel):
    period: str
    problems_solved: int
    total_submissions: int
    accepted_submissions: int

class StruggleProblemOut(BaseCamelModel):
    problem_id: str
    title: str
    slug: str
    difficulty: str
    total_attempts: int
    failed_attempts: int
    failed_submissions: int
    status: str
    topics: List[str]

class ActivityDayOut(BaseCamelModel):
    date: str
    submissions: int
    accepted: int
    solved: int
    minutes_active: int

class TimelineEventOut(BaseCamelModel):
    id: str
    kind: str
    title: str
    detail: str
    problem_slug: Optional[str] = None
    language: Optional[str] = None
    occurred_at: str

class AnalyticsOut(BaseCamelModel):
    overview: AnalyticsOverviewOut
    topics: List[TopicStatOut]
    difficulties: List[DifficultyStatOut]
    languages: List[LanguageStatOut]
    progress: List[ProgressOverTimeOut]
    struggles: List[StruggleProblemOut]
