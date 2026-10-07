"""Deterministic conceptual similarity scoring for candidate problems.

Similarity is intentionally **not** "shares a topic tag".  A candidate is
scored across several independent, explainable dimensions, and the ranking
weights live in exactly one place (:data:`DEFAULT_SIMILARITY_WEIGHTS`) so the
behaviour can be tuned and tested without hunting for magic numbers.

Every score returns the component breakdown *and* human-readable reasons, so a
recommendation can always explain itself.
"""

from __future__ import annotations

from dataclasses import dataclass, fields

from codememory.learning.models import ProblemCandidate, SimilarityBreakdown
from codememory.learning.taxonomy import (
    concept_groups_of,
    data_structures_of,
    skill_label,
)

_DIFFICULTY_ORDER = {"Easy": 0, "Medium": 1, "Hard": 2, "Unknown": -1}


@dataclass(frozen=True)
class SimilarityWeights:
    """Centralised weights for the conceptual similarity score."""

    pattern_match: float = 3.0
    concept_match: float = 1.5
    topic_match: float = 1.0
    data_structure_match: float = 1.0
    improvement_target_match: float = 2.0
    difficulty_fit: float = 1.0
    progression_value: float = 1.5

    def max_total(self) -> float:
        return sum(getattr(self, f.name) for f in fields(self))

    def as_dict(self) -> dict[str, float]:
        return {f.name: getattr(self, f.name) for f in fields(self)}


DEFAULT_SIMILARITY_WEIGHTS = SimilarityWeights()


@dataclass(frozen=True)
class SeedContext:
    """Everything the scorer knows about the user when ranking candidates."""

    seed_topics: tuple[str, ...] = ()
    seed_patterns: tuple[str, ...] = ()
    target_patterns: tuple[str, ...] = ()
    improvement_topics: tuple[str, ...] = ()
    practiced_patterns: tuple[str, ...] = ()
    strength_patterns: tuple[str, ...] = ()
    difficulty_ceiling: str = "Easy"


def _fraction(shared: set[str], total: set[str]) -> float:
    if not total:
        return 0.0
    return min(1.0, len(shared) / len(total))


def _difficulty_fit(candidate_difficulty: str, ceiling: str) -> tuple[float, str | None]:
    """Return a 0..1 fit for a candidate relative to the demonstrated ceiling."""
    cand = _DIFFICULTY_ORDER.get(candidate_difficulty, -1)
    top = _DIFFICULTY_ORDER.get(ceiling, 0)
    if cand < 0:
        return 0.3, None
    if cand == top:
        return 1.0, f"Matches your demonstrated {ceiling} level"
    if cand == top + 1:
        return 0.9, f"One step above your demonstrated {ceiling} level"
    if cand < top:
        return 0.4, f"Below your demonstrated {ceiling} level (consolidation)"
    return 0.1, "Above your demonstrated level, but reachable later"


def _progression_value(
    candidate: ProblemCandidate,
    seed: SeedContext,
) -> tuple[float, str | None]:
    """Reward candidates that advance the user without repeating practice."""
    practiced = set(seed.practiced_patterns)
    candidate_patterns = set(candidate.patterns)
    strengths = set(seed.strength_patterns)

    if candidate_patterns & strengths and not (candidate_patterns & practiced - strengths):
        return 0.6, "Extends an area you have already demonstrated"

    novel_foundational = {
        p for p in candidate_patterns if p and p not in practiced
    }
    if novel_foundational and not (candidate_patterns & practiced):
        return 1.0, "Introduces a pattern you have not practised yet"

    if candidate_patterns & practiced:
        return 0.3, "Reinforces a pattern already practised"
    return 0.2, None


def score_candidate(
    candidate: ProblemCandidate,
    seed: SeedContext,
    weights: SimilarityWeights = DEFAULT_SIMILARITY_WEIGHTS,
) -> SimilarityBreakdown:
    """Score a single candidate against the seed context.

    Returns a fully explained :class:`SimilarityBreakdown`.  The score is
    deterministic: identical inputs always produce an identical result.
    """
    breakdown = SimilarityBreakdown()
    reasons: list[str] = []

    cand_patterns = set(candidate.patterns)
    seed_patterns = set(seed.seed_patterns)
    cand_topics = {t.strip() for t in candidate.topics if t and t.strip()}
    seed_topics = {t.strip() for t in seed.seed_topics if t and t.strip()}
    targets = set(seed.target_patterns) | set(seed.seed_patterns)

    # 1. Shared algorithmic pattern ---------------------------------------
    shared_patterns = cand_patterns & seed_patterns
    breakdown.pattern_match = _fraction(shared_patterns, seed_patterns)
    if shared_patterns:
        reasons.append("Shares the pattern: " + ", ".join(skill_label(p) for p in sorted(shared_patterns)))

    # 2. Shared concept family -------------------------------------------
    seed_groups = set(concept_groups_of(seed_patterns))
    cand_groups = set(concept_groups_of(cand_patterns))
    shared_groups = seed_groups & cand_groups
    breakdown.concept_match = _fraction(shared_groups, seed_groups)
    if shared_groups:
        pretty = ", ".join(sorted(g.replace("_", " ") for g in shared_groups))
        reasons.append(f"Same concept family: {pretty}")

    # 3. Shared topic tags ------------------------------------------------
    shared_topics = cand_topics & seed_topics
    breakdown.topic_match = _fraction(shared_topics, seed_topics)
    if shared_topics:
        reasons.append("Shares topic tags: " + ", ".join(sorted(shared_topics)))

    # 4. Shared data structure -------------------------------------------
    seed_ds = set(data_structures_of(seed_patterns))
    cand_ds = set(data_structures_of(cand_patterns))
    shared_ds = seed_ds & cand_ds
    breakdown.data_structure_match = _fraction(shared_ds, seed_ds)
    if shared_ds:
        reasons.append("Uses the same data structure: " + ", ".join(sorted(shared_ds)))

    # 5. Improvement-target match ----------------------------------------
    target_hit = cand_patterns & targets
    improvement_topics = {t.strip() for t in seed.improvement_topics if t and t.strip()}
    topic_hit = cand_topics & improvement_topics
    breakdown.improvement_target_match = _fraction(target_hit | topic_hit, targets | improvement_topics)
    if topic_hit:
        reasons.append(
            "Targets a recorded improvement area: " + ", ".join(sorted(topic_hit))
        )
    elif target_hit:
        reasons.append(
            "Targets an improvement pattern: "
            + ", ".join(skill_label(p) for p in sorted(target_hit))
        )

    # 6. Difficulty fit ---------------------------------------------------
    breakdown.difficulty_fit, difficulty_reason = _difficulty_fit(
        candidate.difficulty, seed.difficulty_ceiling
    )
    if difficulty_reason:
        reasons.append(difficulty_reason)

    # 7. Progression value ------------------------------------------------
    breakdown.progression_value, progression_reason = _progression_value(candidate, seed)
    if progression_reason:
        reasons.append(progression_reason)

    breakdown.total = round(
        breakdown.pattern_match * weights.pattern_match
        + breakdown.concept_match * weights.concept_match
        + breakdown.topic_match * weights.topic_match
        + breakdown.data_structure_match * weights.data_structure_match
        + breakdown.improvement_target_match * weights.improvement_target_match
        + breakdown.difficulty_fit * weights.difficulty_fit
        + breakdown.progression_value * weights.progression_value,
        4,
    )
    breakdown.reasons = reasons
    return breakdown
