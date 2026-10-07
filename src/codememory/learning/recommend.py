"""Deterministic "solve next right now" recommendations.

Kept deliberately separate from the roadmap: the next-problem answer is driven
by the **most recent solve**, while the roadmap is driven by the **whole
history**.  They must not be identical lists.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from codememory.ai.models import ProblemRecommendation
from codememory.learning.candidates import build_seed_context, rank_candidates
from codememory.learning.models import LearningProfile, ProblemCandidate
from codememory.learning.similarity import (
    DEFAULT_SIMILARITY_WEIGHTS,
    SeedContext,
    SimilarityWeights,
)
from codememory.learning.taxonomy import skill_label


@dataclass(frozen=True)
class RecommendationOptions:
    limit: int = 3
    weights: SimilarityWeights = DEFAULT_SIMILARITY_WEIGHTS
    distinct_primary_pattern: bool = True


DEFAULT_RECOMMENDATION_OPTIONS = RecommendationOptions()


def _struggle_patterns(profile: LearningProfile) -> list[str]:
    ordered: list[str] = []
    for signal in profile.improvement_areas:
        for pattern in signal.patterns:
            if pattern not in ordered:
                ordered.append(pattern)
    return ordered


def _improvement_topics(profile: LearningProfile) -> list[str]:
    ordered: list[str] = []
    for signal in profile.improvement_areas:
        for topic in signal.topics:
            if topic not in ordered:
                ordered.append(topic)
    return ordered


def _strength_patterns(profile: LearningProfile) -> list[str]:
    ordered: list[str] = []
    for signal in profile.strengths:
        for pattern in signal.patterns:
            if pattern not in ordered:
                ordered.append(pattern)
    return ordered


def build_seed_context_for_next(profile: LearningProfile) -> SeedContext:
    """The next-problem seed: latest solve first, sharpened by known gaps."""
    target_patterns: list[str] = []
    for pattern in list(profile.seed_patterns) + _struggle_patterns(profile):
        if pattern not in target_patterns:
            target_patterns.append(pattern)
    return build_seed_context(
        profile,
        target_patterns=target_patterns,
        improvement_topics=_improvement_topics(profile),
        strength_patterns=_strength_patterns(profile),
    )


def build_next_recommendations(
    profile: LearningProfile,
    candidates: Sequence[ProblemCandidate],
    options: RecommendationOptions | None = None,
    *,
    evidence_refs: Sequence[str] = (),
) -> list[ProblemRecommendation]:
    """Rank real, unused candidates against the latest-solve context."""
    options = options or DEFAULT_RECOMMENDATION_OPTIONS
    seed = build_seed_context_for_next(profile)
    ranked = rank_candidates(candidates, seed, options.weights)

    chosen = []
    seen_primary: set[str] = set()
    for item in ranked:
        if item.score.total <= 0 and chosen:
            continue
        patterns = item.candidate.patterns
        primary = patterns[0] if patterns else ""
        if options.distinct_primary_pattern and primary and primary in seen_primary:
            continue
        if primary:
            seen_primary.add(primary)
        chosen.append(item)
        if len(chosen) >= options.limit:
            break

    recommendations: list[ProblemRecommendation] = []
    for item in chosen:
        candidate = item.candidate
        reasons = list(item.score.reasons)
        primary_skill = skill_label(candidate.patterns[0]) if candidate.patterns else "DSA problem solving"
        rationale = (
            "Recommended because it "
            + "; ".join(part[0].lower() + part[1:] for part in reasons[:3])
            + "."
            if reasons
            else f"Recommended to reinforce {primary_skill}."
        )
        recommendations.append(
            ProblemRecommendation(
                problem_slug=candidate.slug,
                title=candidate.title,
                difficulty=candidate.difficulty,
                topics=list(candidate.topics),
                url=candidate.url,
                is_revision=False,
                selection_rationale=rationale,
                target_skill=primary_skill,
                prior_attempt_connection=(
                    "Chosen relative to your most recent solve"
                    + (f" ({profile.seed_problem_slug})" if profile.seed_problem_slug else "")
                    + "."
                ),
                difficulty_rationale=(
                    f"{candidate.difficulty} difficulty fits your demonstrated "
                    f"{profile.difficulty_ceiling} level."
                ),
                solving_focus=(
                    f"Practise {primary_skill} deliberately: state the invariant and "
                    "complexity before you write code."
                ),
                reflection_checklist=[
                    "Did I state time and space complexity before coding?",
                    "Is there a more efficient data structure for this?",
                    "Did I handle empty input, single elements, and duplicates?",
                ],
                next_step_after=(
                    "Log your attempt, then read the optimization explanation for this "
                    "problem."
                ),
                evidence_refs=list(evidence_refs),
                similarity_reasons=reasons,
                source=candidate.source,
                source_problem_slug=profile.seed_problem_slug,
            )
        )
    return recommendations
