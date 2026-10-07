"""Candidate retrieval, filtering, de-duplication and ranking.

This module owns the *whole* candidate pipeline:

    source -> normalise -> de-duplicate -> filter -> rank

De-duplication is by canonical identity (slug, plus a normalised-title guard
for slug drift between sources).  Everything is deterministic and explainable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence

from codememory.domain.models import generate_slug
from codememory.learning.models import ProblemCandidate, RankedCandidate
from codememory.learning.similarity import (
    DEFAULT_SIMILARITY_WEIGHTS,
    SeedContext,
    SimilarityWeights,
    score_candidate,
)


@dataclass
class CandidateFilterPolicy:
    """Policy controlling which candidates may be recommended.

    ``exclude_recent`` defaults to ``False`` on purpose: a problem that was only
    *attempted* (and not solved) is still a legitimate practice target, and the
    regression suite requires wrong-answer-only problems to remain
    recommendable.  Callers that want a strict cooldown can opt in.
    """

    exclude_solved: bool = True
    exclude_recent: bool = False
    allow_revision: bool = False
    require_topics: bool = False
    exclude_premium: bool = False


@dataclass
class CandidatePool:
    """The result of retrieval: accepted candidates plus a rejection audit."""

    accepted: list[ProblemCandidate] = field(default_factory=list)
    rejected: dict[str, str] = field(default_factory=dict)


def canonical_title_key(title: str) -> str:
    """Normalised title key used as a second de-duplication guard."""
    return generate_slug(title or "")


def filter_candidates(
    candidates: Iterable[ProblemCandidate],
    *,
    profile,
    policy: CandidateFilterPolicy | None = None,
    extra_excluded_keys: Iterable[str] = (),
) -> CandidatePool:
    """Filter a raw candidate stream down to recommendable problems.

    Every rejection is recorded with a machine-readable reason so the audit is
    testable and the roadmap validator can explain why a phase is short.
    """
    policy = policy or CandidateFilterPolicy()
    solved = set(profile.solved_keys)
    recent = set(profile.recent_keys)
    excluded = {k.strip().lower() for k in extra_excluded_keys if k}
    seed_key = (profile.seed_problem_key or "").strip().lower()

    pool = CandidatePool()
    seen_keys: set[str] = set()
    seen_titles: set[str] = set()

    for candidate in candidates:
        key = candidate.key
        if not key:
            pool.rejected[key or "<empty>"] = "missing_identity"
            continue
        if key in seen_keys:
            pool.rejected[key] = "duplicate_identity"
            continue
        title_key = canonical_title_key(candidate.title)
        if title_key and title_key in seen_titles:
            pool.rejected[key] = "duplicate_title"
            continue
        if not candidate.metadata_complete or not candidate.title or not candidate.slug:
            pool.rejected[key] = "insufficient_metadata"
            continue
        if key == seed_key:
            pool.rejected[key] = "seed_problem"
            continue
        if policy.exclude_solved and not policy.allow_revision and key in solved:
            pool.rejected[key] = "already_solved"
            continue
        if policy.exclude_recent and key in recent:
            pool.rejected[key] = "recently_attempted"
            continue
        if key in excluded:
            pool.rejected[key] = "already_used"
            continue
        if policy.exclude_premium and candidate.premium_only:
            pool.rejected[key] = "premium_only"
            continue
        if policy.require_topics and not candidate.topics:
            pool.rejected[key] = "no_topics"
            continue

        seen_keys.add(key)
        if title_key:
            seen_titles.add(title_key)
        pool.accepted.append(candidate)

    return pool


def rank_candidates(
    candidates: Sequence[ProblemCandidate],
    seed: SeedContext,
    weights: SimilarityWeights = DEFAULT_SIMILARITY_WEIGHTS,
) -> list[RankedCandidate]:
    """Rank candidates by conceptual similarity, deterministically.

    Ties are broken by title then slug so identical inputs always yield an
    identical ordering.
    """
    ranked = [
        RankedCandidate(candidate=candidate, score=score_candidate(candidate, seed, weights))
        for candidate in candidates
    ]
    ranked.sort(
        key=lambda r: (
            -r.score.total,
            -(1 if r.candidate.source == "local_catalog" else 0),
            r.candidate.title.lower(),
            r.candidate.slug,
        )
    )
    return ranked


def build_seed_context(
    profile,
    *,
    target_patterns: Sequence[str] = (),
    improvement_topics: Sequence[str] = (),
    strength_patterns: Sequence[str] = (),
) -> SeedContext:
    """Assemble the scorer's view of the user from a :class:`LearningProfile`."""
    return SeedContext(
        seed_topics=tuple(profile.seed_topics),
        seed_patterns=tuple(profile.seed_patterns),
        target_patterns=tuple(target_patterns),
        improvement_topics=tuple(improvement_topics),
        practiced_patterns=tuple(profile.patterns_practiced),
        strength_patterns=tuple(strength_patterns),
        difficulty_ceiling=profile.difficulty_ceiling,
    )
