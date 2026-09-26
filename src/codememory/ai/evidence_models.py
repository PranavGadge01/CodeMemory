"""Typed evidence models for the grounded personalized insight pipeline.

Every piece of evidence carries a stable semantic ``evidence_id`` and a
``source_type`` tag so downstream consumers can trace each claim back to the
deterministic system or cached AI analysis that produced it.
"""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_evidence_id(*parts: str) -> str:
    """Build a stable, dotted semantic evidence ID from path segments.

    >>> _make_evidence_id("analytics", "topic_stats", "Dynamic Programming", "acceptance_rate")
    'analytics.topic_stats.dynamic_programming.acceptance_rate'
    """
    return ".".join(
        p.strip().lower().replace(" ", "_").replace("-", "_")
        for p in parts
        if p and p.strip()
    )


# ---------------------------------------------------------------------------
# Leaf models
# ---------------------------------------------------------------------------

class EvidenceItem(BaseModel):
    """Single traceable piece of evidence."""

    evidence_id: str = Field(description="Stable semantic ID, e.g. 'analytics.overview.acceptance_rate'")
    source: str = Field(description="Broader source category, e.g. 'analytics.overview'")
    source_type: Literal["deterministic", "ai_analysis"] = "deterministic"
    label: str = Field(description="Human-readable label")
    value: Any = Field(description="The deterministic value")
    unit: str | None = None
    sample_size: int | None = None


class EvidenceMetrics(BaseModel):
    """Deterministic numeric metrics collected from AnalyticsService."""

    overview: dict[str, Any] = Field(default_factory=dict)
    topic_stats: list[dict[str, Any]] = Field(default_factory=list)
    difficulty_stats: list[dict[str, Any]] = Field(default_factory=list)
    attempt_stats: dict[str, Any] = Field(default_factory=dict)


class EvidencePatterns(BaseModel):
    """Deterministic pattern analysis from PatternAnalyzer."""

    weak_topics: list[dict[str, Any]] = Field(default_factory=list)
    high_failure_topics: list[dict[str, Any]] = Field(default_factory=list)
    repeated_tle_problems: list[str] = Field(default_factory=list)
    repeated_wa_problems: list[str] = Field(default_factory=list)
    brute_force_before_optimized_problems: list[str] = Field(default_factory=list)
    high_attempt_problems: list[dict[str, Any]] = Field(default_factory=list)
    improvement_patterns: list[dict[str, Any]] = Field(default_factory=list)
    unpracticed_topics: list[dict[str, Any]] = Field(default_factory=list)


class SubmissionSnapshot(BaseModel):
    """Lightweight summary of a cached SubmissionAnalysis."""

    submission_id: str
    problem_title: str
    approach: str
    time_complexity: str
    space_complexity: str
    correctness_summary: str
    potential_issues: str | None = None


class ProblemSnapshot(BaseModel):
    """Lightweight summary of a Problem's state."""

    problem_id: str
    title: str
    slug: str
    difficulty: str
    topics: list[str] = Field(default_factory=list)
    total_attempts: int = 0
    status: str = "Unsolved"  # "Solved" | "Unsolved"


class EvidenceComparison(BaseModel):
    """Named relative comparison between two deterministic rates."""

    evidence_id: str = Field(description="Stable semantic ID for this comparison")
    label: str
    topic_evidence_id: str = Field(description="Evidence ID of the topic-specific rate")
    overall_evidence_id: str = Field(description="Evidence ID of the overall baseline rate")
    topic_rate: float
    overall_rate: float
    delta: float


# ---------------------------------------------------------------------------
# Top-level evidence bundle
# ---------------------------------------------------------------------------

class InsightEvidence(BaseModel):
    """Structured, serializable evidence bundle with provenance.

    The ``evidence_id`` on this top-level bundle is a UUID identifying this
    particular generated evidence snapshot. Individual ``EvidenceItem`` and
    ``EvidenceComparison`` entries carry stable semantic IDs.
    """

    evidence_id: str = Field(default_factory=lambda: str(uuid4()))
    scope: str = Field(description="'full_profile' | 'topic:<name>' | 'problem:<identifier>'")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    items: list[EvidenceItem] = Field(default_factory=list)
    metrics: EvidenceMetrics = Field(default_factory=EvidenceMetrics)
    patterns: EvidencePatterns = Field(default_factory=EvidencePatterns)
    supporting_submissions: list[SubmissionSnapshot] = Field(default_factory=list)
    supporting_problems: list[ProblemSnapshot] = Field(default_factory=list)
    comparisons: list[EvidenceComparison] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)

    def all_evidence_ids(self) -> set[str]:
        """Return every valid evidence ID in this bundle.

        Includes IDs from ``items``, ``comparisons``, and the top-level
        ``evidence_id``.
        """
        ids: set[str] = {self.evidence_id}
        for item in self.items:
            ids.add(item.evidence_id)
        for comp in self.comparisons:
            ids.add(comp.evidence_id)
        return ids
