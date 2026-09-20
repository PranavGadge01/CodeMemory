from typing import List, Optional
from datetime import datetime
from api.schemas.common import BaseCamelModel

class RevisionScoreBreakdownOut(BaseCamelModel):
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

class RevisionQueueItemOut(BaseCamelModel):
    problem_id: str
    title: str
    slug: str
    difficulty: str
    priority_score: float
    last_activity_at: Optional[datetime] = None
    topics: List[str]
    status: Optional[str] = None
    confidence: Optional[str] = None
    reason: Optional[str] = None
    breakdown: RevisionScoreBreakdownOut
