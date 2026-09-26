"""Response models for the filtered submission list endpoint."""

from api.schemas.common import PaginatedResponse, BaseCamelModel
from api.schemas.problems import SubmissionOut


class SubmissionSummaryOut(BaseCamelModel):
    """Aggregate metrics for the complete filtered set, before pagination."""

    total: int
    accepted: int
    failed: int
    acceptance_rate: float
    problem_count: int
    language_count: int


class SubmissionListOut(PaginatedResponse[SubmissionOut]):
    """A page of submission rows plus full-set aggregate metrics."""

    summary: SubmissionSummaryOut
