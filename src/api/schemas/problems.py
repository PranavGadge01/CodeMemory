from datetime import datetime
from typing import List, Optional
from pydantic import Field
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
    code: Optional[str] = None
    language: str
    status: str
    runtime_ms: Optional[float] = None
    memory_mb: Optional[float] = None
    submitted_at: datetime
    error_message: Optional[str] = None
    submission_hash: str
    source_provider: Optional[str] = None
    source_account: Optional[str] = None

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
    # Summary fields the problems table renders directly, so the list endpoint
    # does not force the client to fetch every problem individually.
    attempt_count: int = 0
    accepted_count: int = 0
    submission_count: int = 0
    languages: List[str] = Field(default_factory=list)
    best_runtime: Optional[float] = None
    best_memory: Optional[float] = None
    last_activity_at: Optional[datetime] = None
    status: str = "Untouched"

    @classmethod
    def from_problem(cls, problem) -> "ProblemListItemOut":
        """Project a domain problem into the table summary row."""
        from codememory.domain.enums import SubmissionStatus

        submissions = [s for a in problem.attempts for s in a.submissions]
        accepted = [s for s in submissions if s.status == SubmissionStatus.ACCEPTED]

        languages: List[str] = []
        for submission in sorted(submissions, key=lambda s: s.submitted_at):
            if submission.language and submission.language not in languages:
                languages.append(submission.language)

        runtimes = [s.runtime_ms for s in accepted if s.runtime_ms is not None]
        memories = [s.memory_mb for s in accepted if s.memory_mb is not None]

        if any(a.is_accepted for a in problem.attempts):
            status = "Solved"
        elif problem.attempts:
            status = "Attempted"
        else:
            status = "Untouched"

        last_activity = (
            max(submissions, key=lambda s: s.submitted_at).submitted_at
            if submissions
            else problem.updated_at
        )

        return cls(
            id=problem.id,
            title=problem.title,
            slug=problem.slug,
            difficulty=problem.difficulty.value,
            platform=problem.platform.value if hasattr(problem.platform, "value") else str(problem.platform),
            topics=list(problem.topics),
            created_at=problem.created_at,
            updated_at=problem.updated_at,
            attempt_count=len(problem.attempts),
            accepted_count=len(accepted),
            submission_count=len(submissions),
            languages=languages,
            best_runtime=min(runtimes) if runtimes else None,
            best_memory=min(memories) if memories else None,
            last_activity_at=last_activity,
            status=status,
        )

class EvolutionStepOut(BaseCamelModel):
    attempt_number: int
    status: str
    approach: str
    time_complexity: str
    space_complexity: str
    runtime: Optional[str] = None
    memory: Optional[str] = None
    timestamp: str

class SolutionEvolutionOut(BaseCamelModel):
    problem_id: str
    problem_title: str
    total_attempts: int
    steps: List[EvolutionStepOut]
    evolution_narrative: str
    key_breakthrough: Optional[str] = None
    better_approach: Optional[str] = None
    similar_problems: List[str] = Field(default_factory=list)


class SearchResultProblem(BaseCamelModel):
    title: str
    slug: str
    difficulty: str
    topics: List[str]
    platform: str


class SearchResultSubmission(BaseCamelModel):
    id: str
    title: str
    slug: str
    language: str
    status: str
    runtime_ms: Optional[float] = None
    memory_mb: Optional[float] = None
    source_provider: Optional[str] = None
    source_account: Optional[str] = None


class SearchResultItem(BaseCamelModel):
    type: str  # "problem" | "submission" | "knowledge"
    id: str
    title: str
    slug: str
    metadata: dict = {}


class SearchResponse(BaseCamelModel):
    query: str
    results: List[SearchResultItem]
