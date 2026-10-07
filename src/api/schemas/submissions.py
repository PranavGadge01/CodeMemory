"""Response models for the filtered submission list endpoint."""

from typing import Dict, Optional

from pydantic import Field

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


class SubmissionFilterOptionsOut(BaseCamelModel):
    """Counts over the complete unfiltered set, used by the filter chips.

    Kept separate from ``summary`` (which describes the *filtered* set) so the
    chip numbers stay stable as a filter narrows the table.
    """

    total: int = 0
    status_counts: Dict[str, int] = Field(default_factory=dict)
    language_counts: Dict[str, int] = Field(default_factory=dict)


class SubmissionListItemOut(SubmissionOut):
    """A submission row enriched with the problem metadata the table links to."""

    problem_title: Optional[str] = None
    problem_slug: Optional[str] = None


class SubmissionListOut(PaginatedResponse[SubmissionListItemOut]):
    """A page of submission rows plus full-set aggregate metrics."""

    summary: SubmissionSummaryOut
    filter_options: SubmissionFilterOptionsOut = Field(default_factory=SubmissionFilterOptionsOut)
