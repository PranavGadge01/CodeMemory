from datetime import datetime
from typing import List, Optional
from api.schemas.common import BaseCamelModel

class SolutionAnalysisOut(BaseCamelModel):
    approach_name: str
    time_complexity: str
    space_complexity: str
    key_insights: List[str]
    trade_offs: Optional[str] = None
    bottleneck: Optional[str] = None

class SubmissionOut(BaseCamelModel):
    id: str
    problem_id: str
    attempt_id: Optional[str] = None
    code: str
    language: str
    status: str
    runtime_ms: Optional[float] = None
    memory_mb: Optional[float] = None
    submitted_at: datetime
    error_message: Optional[str] = None
    submission_hash: str

class AttemptOut(BaseCamelModel):
    id: str
    problem_id: str
    attempt_number: int
    approach_summary: str
    reasoning: Optional[str] = None
    mistakes: List[str]
    analysis: Optional[SolutionAnalysisOut] = None
    status: str
    created_at: datetime
    updated_at: datetime
    submissions: List[SubmissionOut]

class ProblemNoteOut(BaseCamelModel):
    id: str
    problem_id: str
    attempt_id: Optional[str] = None
    content: str
    note_type: str
    created_at: datetime

class ProblemOut(BaseCamelModel):
    id: str
    title: str
    slug: str
    difficulty: str
    platform: str
    url: Optional[str] = None
    topics: List[str]
    statement: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    attempts: List[AttemptOut]
    notes: List[ProblemNoteOut]

class ProblemListItemOut(BaseCamelModel):
    id: str
    title: str
    slug: str
    difficulty: str
    platform: str
    topics: List[str]
    created_at: datetime
    updated_at: datetime
