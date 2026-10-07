"""Typed models for the deterministic learning layer.

These models are deliberately separate from the persisted domain entities in
``codememory.domain.models``.  A :class:`ProblemCandidate` may describe a
problem that exists only in a remote, read-only catalogue -- it is *never*
written to storage and never becomes user history.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

from codememory.learning.taxonomy import patterns_for_topics


SignalCategory = Literal["observed", "interpretation", "recommendation"]


class ProfileSignal(BaseModel):
    """A single learning signal carrying its own evidence and epistemic label.

    ``category`` distinguishes what was *observed* (a fact recountable from the
    data) from an *interpretation* (a cautious reading of those facts) and from
    a *recommendation* (a suggested next action).  Downstream consumers must
    never present an interpretation as an observed fact.
    """

    key: str
    category: SignalCategory = "observed"
    statement: str
    evidence: str = ""
    topics: list[str] = Field(default_factory=list)
    patterns: list[str] = Field(default_factory=list)
    sample_size: int = 0
    evidence_refs: list[str] = Field(default_factory=list)


class TopicObservation(BaseModel):
    """Deterministic per-topic statistics derived from submission history."""

    topic: str
    problems: int = 0
    solved: int = 0
    submissions: int = 0
    accepted: int = 0
    failed: int = 0
    success_rate_pct: float = 0.0
    total_attempts: int = 0


class DifficultyObservation(BaseModel):
    """Deterministic per-difficulty statistics."""

    difficulty: str
    problems: int = 0
    solved: int = 0
    submissions: int = 0
    accepted: int = 0


class ProblemCandidate(BaseModel):
    """A normalised, rankable candidate problem from a verified problem source.

    Canonical identity is the normalised slug when present, falling back to the
    source problem id.  ``source`` records provenance so the UI can distinguish
    a problem from the user's own catalogue from one fetched from LeetCode.
    """

    problem_id: str
    slug: str
    title: str
    difficulty: str = "Unknown"
    topics: list[str] = Field(default_factory=list)
    url: str | None = None
    source: str = "local_catalog"
    premium_only: bool = False
    metadata_complete: bool = True

    @property
    def key(self) -> str:
        """Canonical de-duplication key (slug-first, id fallback)."""
        slug = (self.slug or "").strip().lower()
        if slug:
            return slug
        return f"id:{(self.problem_id or '').strip().lower()}"

    @property
    def patterns(self) -> tuple[str, ...]:
        """Conceptual patterns implied by this candidate's topic tags."""
        return patterns_for_topics(self.topics)

    def model_post_init(self, __context: Any) -> None:
        if not self.metadata_complete:
            return
        if not self.title or not self.slug:
            self.metadata_complete = False


class SimilarityBreakdown(BaseModel):
    """Explainable component scores for a candidate's similarity to a seed."""

    pattern_match: float = 0.0
    concept_match: float = 0.0
    topic_match: float = 0.0
    data_structure_match: float = 0.0
    improvement_target_match: float = 0.0
    difficulty_fit: float = 0.0
    progression_value: float = 0.0
    total: float = 0.0
    reasons: list[str] = Field(default_factory=list)


class RankedCandidate(BaseModel):
    """A candidate paired with its similarity score and retrieval provenance."""

    candidate: ProblemCandidate
    score: SimilarityBreakdown


class LearningProfile(BaseModel):
    """Deterministic, whole-history learning profile for one account.

    The profile is pure data: every field is derived from stored problems and
    submissions.  It carries its own ``limitations`` so sparse histories are
    never over-interpreted.
    """

    account: str | None = None
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    total_problems: int = 0
    solved_problems: int = 0
    attempted_problems: int = 0
    unsolved_problems: int = 0
    total_submissions: int = 0
    accepted_submissions: int = 0
    failed_submissions: int = 0
    first_attempt_accepts: int = 0

    languages: list[str] = Field(default_factory=list)
    topics: list[TopicObservation] = Field(default_factory=list)
    difficulties: list[DifficultyObservation] = Field(default_factory=list)
    patterns_practiced: list[str] = Field(default_factory=list)
    strengths: list[ProfileSignal] = Field(default_factory=list)
    improvement_areas: list[ProfileSignal] = Field(default_factory=list)
    unpracticed_topics: list[str] = Field(default_factory=list)
    unpracticed_patterns: list[str] = Field(default_factory=list)
    recurring_mistakes: list[ProfileSignal] = Field(default_factory=list)

    solved_keys: list[str] = Field(default_factory=list)
    attempted_keys: list[str] = Field(default_factory=list)
    recent_keys: list[str] = Field(default_factory=list)
    seed_problem_key: str | None = None
    seed_problem_slug: str | None = None
    seed_patterns: list[str] = Field(default_factory=list)
    seed_topics: list[str] = Field(default_factory=list)

    difficulty_ceiling: str = "Easy"
    breadth: int = 0
    limitations: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)

    def topic_map(self) -> dict[str, TopicObservation]:
        return {t.topic: t for t in self.topics}

    def practiced_pattern_set(self) -> set[str]:
        return set(self.patterns_practiced)

    def summary_line(self) -> str:
        """One factual sentence describing the profile's scope."""
        return (
            f"{self.solved_problems} solved / {self.total_problems} tracked problems "
            f"across {self.breadth} topics; {self.total_submissions} submissions recorded."
        )
