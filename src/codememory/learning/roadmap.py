"""Deterministic, whole-history roadmap generation and validation.

Design goals that the previous implementation missed:

* Phases are derived from the user's **entire** history, not a fixed template.
* Phase 1 is strongly influenced by the most recent solve; later phases
  progressively address adjacent patterns, prerequisite gaps and synthesis.
* A single ``used_keys`` set is threaded across every phase, so a problem can
  never appear twice.
* Every problem is a *real* candidate from the verified source, and every phase
  is validated before it is returned.  Invalid phases are dropped, never
  papered over.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from codememory.ai.models import (
    PersonalizedRoadmap,
    ProblemRecommendation,
    RoadmapMilestone,
)
from codememory.learning.candidates import (
    RankedCandidate,
    RankedCandidate as _RankedCandidate,
    build_seed_context,
    canonical_title_key,
    rank_candidates,
)
from codememory.learning.models import LearningProfile, ProblemCandidate
from codememory.learning.similarity import (
    DEFAULT_SIMILARITY_WEIGHTS,
    SeedContext,
    SimilarityWeights,
)
from codememory.learning.taxonomy import (
    adjacent_of,
    describe_patterns,
    is_foundational,
    prerequisites_of,
    skill_label,
)

_DIFFICULTY_ORDER = {"Easy": 0, "Medium": 1, "Hard": 2, "Unknown": -1}
_PHASE_STATUS = ("in_progress", "available", "locked", "locked", "locked")


@dataclass(frozen=True)
class RoadmapOptions:
    """Configurable, centralised roadmap generation policy."""

    min_problems_per_phase: int = 3
    max_problems_per_phase: int = 5
    min_phases: int = 2
    max_phases: int = 5
    weights: SimilarityWeights = DEFAULT_SIMILARITY_WEIGHTS


DEFAULT_ROADMAP_OPTIONS = RoadmapOptions()


@dataclass
class PhaseSpec:
    """A planned learning phase before problems are attached."""

    phase_id: str
    title: str
    objective: str
    rationale: str
    target_patterns: tuple[str, ...]
    prerequisites: list[str] = field(default_factory=list)
    target_skills: list[str] = field(default_factory=list)
    kind: str = "reinforcement"
    improvement_topics: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Phase planning
# ---------------------------------------------------------------------------


def _difficulty_rank(difficulty: str) -> int:
    return _DIFFICULTY_ORDER.get(difficulty, -1)


def _patterns_from_signals(signals: Sequence) -> list[str]:
    ordered: list[str] = []
    for signal in signals:
        for pattern in getattr(signal, "patterns", []) or []:
            if pattern not in ordered:
                ordered.append(pattern)
    return ordered


def _topics_from_signals(signals: Sequence) -> list[str]:
    ordered: list[str] = []
    for signal in signals:
        for topic in getattr(signal, "topics", []) or []:
            if topic not in ordered:
                ordered.append(topic)
    return ordered


def _is_struggle_signal(signal) -> bool:
    """True only for signals backed by concrete failure/refinement evidence.

    Coverage gaps (``gap.*``) are deliberately excluded: "not practised yet" is
    not the same as "struggles with", and must not drive the reinforcement phase.
    """
    key = getattr(signal, "key", "") or ""
    return (
        key.startswith("struggle.")
        or key.startswith("refinement.")
        or key.startswith("mistakes.")
    )


def plan_phase_specs(profile: LearningProfile, options: RoadmapOptions | None = None) -> list[PhaseSpec]:
    """Derive an ordered, diverse set of learning phases from the profile."""
    options = options or DEFAULT_ROADMAP_OPTIONS
    specs: list[PhaseSpec] = []

    seed_patterns = list(profile.seed_patterns)
    struggle_signals = [s for s in profile.improvement_areas if _is_struggle_signal(s)]
    struggle_patterns = _patterns_from_signals(struggle_signals)
    strength_patterns = _patterns_from_signals(profile.strengths)
    improvement_topics = _topics_from_signals(struggle_signals)
    practiced = list(profile.patterns_practiced)

    used_patterns: set[str] = set()

    def add(
        *,
        title: str,
        objective: str,
        rationale: str,
        targets: Sequence[str],
        kind: str,
        extra_topics: Sequence[str] = (),
    ) -> None:
        unique_targets = [p for p in targets if p and p not in used_patterns]
        if not unique_targets:
            return
        used_patterns.update(unique_targets)
        prerequisites: list[str] = []
        for pattern in unique_targets:
            for prereq in prerequisites_of(pattern):
                if prereq not in prerequisites and prereq not in unique_targets:
                    prerequisites.append(prereq)
        specs.append(
            PhaseSpec(
                phase_id=f"phase-{len(specs) + 1}",
                title=title,
                objective=objective,
                rationale=rationale,
                target_patterns=tuple(unique_targets),
                prerequisites=[skill_label(p) for p in prerequisites],
                target_skills=[skill_label(p) for p in unique_targets],
                kind=kind,
                improvement_topics=[t for t in extra_topics if t],
            )
        )

    # Phase 1: reinforce whatever the user most recently solved.
    if seed_patterns:
        reinforcing = list(seed_patterns)
        add(
            title=f"Reinforce {describe_patterns(seed_patterns[:2])}",
            objective=(
                "Consolidate the pattern you just used by solving fresh problems that "
                "exercise the same idea under different constraints."
            ),
            rationale=(
                "Your most recent accepted solve used "
                + describe_patterns(seed_patterns[:2])
                + ", so this is the right moment to make it durable."
            ),
            targets=reinforcing,
            kind="seed_reinforcement",
            extra_topics=profile.seed_topics,
        )

    # Phase 2 (+): strengthen a pattern where failures were actually observed.
    observed_struggles = [p for p in struggle_patterns if p and p not in used_patterns]
    if observed_struggles:
        targets = observed_struggles[:2]
        add(
            title=f"Strengthen {describe_patterns(targets)}",
            objective=(
                "Rebuild accuracy and efficiency in a pattern where your submissions "
                "recorded repeated unsuccessful attempts."
            ),
            rationale=(
                "This phase is driven by concrete failure evidence (failed submissions) "
                "rather than topic frequency: "
                + describe_patterns(targets)
                + "."
            ),
            targets=targets,
            kind="struggle_reinforcement",
            extra_topics=improvement_topics,
        )

    # Phase 3: progress into an adjacent pattern (skill progression).
    adjacent_candidates: list[str] = []
    for base in list(seed_patterns) + list(strength_patterns) + list(practiced):
        for adjacent in adjacent_of(base):
            if adjacent not in used_patterns and adjacent not in adjacent_candidates:
                adjacent_candidates.append(adjacent)
    adjacent_candidates = [p for p in adjacent_candidates if p not in practiced] or adjacent_candidates
    if adjacent_candidates:
        targets = adjacent_candidates[:2]
        add(
            title=f"Progress into {describe_patterns(targets)}",
            objective=(
                "Extend what you already know into the closely-related technique that "
                "builds on it."
            ),
            rationale=(
                "These patterns are the natural next step from techniques you have "
                "already used successfully."
            ),
            targets=targets,
            kind="adjacent_progression",
        )

    # Phase 4: close a prerequisite / foundational gap.
    foundational_gaps = [
        p
        for p in profile.unpracticed_patterns
        if is_foundational(p) and p not in used_patterns
    ]
    if foundational_gaps:
        targets = foundational_gaps[:2]
        add(
            title=f"Build foundational {describe_patterns(targets)}",
            objective=(
                "Cover a foundational pattern that has not appeared in your tracked "
                "practice yet."
            ),
            rationale=(
                "No tracked problem exercises this pattern. This is a coverage gap, "
                "not evidence that the topic is difficult for you."
            ),
            targets=targets,
            kind="prerequisite_gap",
        )

    # Phase 5: synthesis -- combine two practised patterns in one phase.
    if len(practiced) >= 2:
        def _combine(first: str, second: str) -> tuple[str, str]:
            return first, second

        synthesis_targets: list[str] = []
        for first in practiced:
            for second in practiced:
                if first == second:
                    continue
                pair = _combine(first, second)
                if pair[0] not in used_patterns and pair[1] not in used_patterns:
                    synthesis_targets = [pair[0], pair[1]]
                    break
            if synthesis_targets:
                break
        if synthesis_targets:
            add(
                title="Combine patterns: synthesis practice",
                objective=(
                    "Solve problems that require choosing between, or combining, "
                    "multiple patterns you already know."
                ),
                rationale=(
                    "Mixed problems test pattern selection, which is the step between "
                    "knowing techniques and using them under interview pressure."
                ),
                targets=synthesis_targets,
                kind="synthesis",
            )

    return specs[: options.max_phases]


# ---------------------------------------------------------------------------
# Problem selection
# ---------------------------------------------------------------------------


def _phase_seed(profile: LearningProfile, phase: PhaseSpec) -> SeedContext:
    """Seed context used to score candidates for a specific phase."""
    return SeedContext(
        seed_topics=tuple(phase.improvement_topics) or tuple(profile.seed_topics),
        seed_patterns=phase.target_patterns,
        target_patterns=phase.target_patterns,
        improvement_topics=tuple(phase.improvement_topics),
        practiced_patterns=tuple(profile.patterns_practiced),
        strength_patterns=tuple(_patterns_from_signals(profile.strengths)),
        difficulty_ceiling=profile.difficulty_ceiling,
    )


def _allowed_difficulty(candidate: ProblemCandidate, ceiling: str) -> bool:
    """Never recommend more than one difficulty band above the demonstrated level."""
    cand = _difficulty_rank(candidate.difficulty)
    top = _difficulty_rank(ceiling)
    if cand < 0:
        return True  # unknown difficulty is allowed but ranks last
    return cand <= top + 1


def _select_phase_problems(
    profile: LearningProfile,
    phase: PhaseSpec,
    ranked: Sequence[RankedCandidate],
    used_keys: set[str],
    options: RoadmapOptions,
) -> list[RankedCandidate]:
    """Select 3-5 real, unused problems for a phase, or [] if impossible."""
    targets = set(phase.target_patterns)
    adjacent: set[str] = set()
    for pattern in phase.target_patterns:
        adjacent.update(adjacent_of(pattern))

    def usable(item: RankedCandidate) -> bool:
        candidate = item.candidate
        if candidate.key in used_keys:
            return False
        if not _allowed_difficulty(candidate, profile.difficulty_ceiling):
            return False
        return True

    primary = [r for r in ranked if usable(r) and (set(r.candidate.patterns) & targets)]
    if len(primary) < options.min_problems_per_phase:
        secondary = [
            r
            for r in ranked
            if usable(r)
            and not (set(r.candidate.patterns) & targets)
            and (set(r.candidate.patterns) & adjacent)
        ]
        primary = primary + [r for r in secondary if r not in primary]

    if not primary:
        return []

    selected = primary[: options.max_problems_per_phase]
    # Present each phase in ascending difficulty so it reads as a progression.
    selected = sorted(
        selected,
        key=lambda r: (
            _difficulty_rank(r.candidate.difficulty) if _difficulty_rank(r.candidate.difficulty) >= 0 else 99,
            -r.score.total,
            r.candidate.title.lower(),
        ),
    )
    if len(selected) < options.min_problems_per_phase:
        return []
    return selected


def _to_recommendation(
    ranked: RankedCandidate,
    phase: PhaseSpec,
    profile: LearningProfile,
    evidence_refs: Sequence[str],
) -> ProblemRecommendation:
    candidate = ranked.candidate
    reasons = list(ranked.score.reasons)
    primary_skill = phase.target_skills[0] if phase.target_skills else "DSA problem solving"
    rationale_parts = reasons[:3] or [f"Reinforces {primary_skill}"]
    rationale = f"Included in '{phase.title}' because it " + "; ".join(
        part[0].lower() + part[1:] if part else part for part in rationale_parts
    ) + "."
    return ProblemRecommendation(
        problem_slug=candidate.slug,
        title=candidate.title,
        difficulty=candidate.difficulty,
        topics=list(candidate.topics),
        url=candidate.url,
        is_revision=False,
        selection_rationale=rationale,
        target_skill=primary_skill,
        prior_attempt_connection=(
            f"Selected from your {candidate.source.replace('_', ' ')} for this phase's "
            f"learning objective."
        ),
        difficulty_rationale=(
            f"{candidate.difficulty} difficulty fits your demonstrated "
            f"{profile.difficulty_ceiling} level."
        ),
        solving_focus=(
            "Aim to explain the invariant, state the complexity before coding, and "
            f"apply {primary_skill} deliberately."
        ),
        reflection_checklist=[
            "Did I state the time and space complexity before coding?",
            "Which pattern does this problem actually require, and why?",
            "Did I test empty inputs, single elements, and duplicates?",
            "Could a different data structure make this simpler or faster?",
        ],
        next_step_after=(
            "Compare your solution with the optimization explanation, then continue to "
            "the next problem in this phase."
        ),
        evidence_refs=list(evidence_refs),
        similarity_reasons=reasons,
        source=candidate.source,
        source_problem_slug=profile.seed_problem_slug,
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


@dataclass
class RoadmapValidation:
    """Result of a validation pass over generated milestones."""

    valid: bool
    violations: list[str] = field(default_factory=list)


def validate_roadmap(
    milestones: Sequence[RoadmapMilestone],
    catalog_keys: set[str],
    options: RoadmapOptions | None = None,
) -> RoadmapValidation:
    """Validate a roadmap against the hard product rules.

    Rejects: phases with fewer than ``min_problems_per_phase`` problems,
    duplicate problems across phases, references to problems that are not real
    candidates, missing objectives/reasons, and phases that all target the same
    single pattern.
    """
    options = options or DEFAULT_ROADMAP_OPTIONS
    violations: list[str] = []
    seen_keys: set[str] = set()
    seen_titles: set[str] = set()
    pattern_signatures: set[frozenset[str]] = set()

    for milestone in milestones:
        if not milestone.title.strip():
            violations.append("phase has empty title")
        if not milestone.learning_objective.strip():
            violations.append(f"phase '{milestone.title}' has empty objective")
        if not milestone.relevance.strip():
            violations.append(f"phase '{milestone.title}' has empty rationale")
        problems = milestone.recommended_problems
        if len(problems) < options.min_problems_per_phase:
            violations.append(
                f"phase '{milestone.title}' has {len(problems)} problems "
                f"(minimum {options.min_problems_per_phase})"
            )
        for rec in problems:
            key = (rec.problem_slug or "").strip().lower()
            title_key = canonical_title_key(rec.title)
            if not key:
                violations.append(f"problem '{rec.title}' has no slug")
            elif key not in catalog_keys:
                violations.append(f"problem '{rec.title}' is not in the verified catalog")
            if key in seen_keys or (title_key and title_key in seen_titles):
                violations.append(f"problem '{rec.title}' appears in more than one phase")
            if not rec.selection_rationale.strip():
                violations.append(f"problem '{rec.title}' has no reason")
            seen_keys.add(key)
            if title_key:
                seen_titles.add(title_key)
        signature = frozenset(
            skill.lower() for skill in (milestone.concepts_to_study or [])
        )
        if signature:
            pattern_signatures.add(signature)

    if len(milestones) > 1 and len(pattern_signatures) == 1:
        violations.append("every phase targets the same pattern")

    return RoadmapValidation(valid=not violations, violations=violations)


def _repair_until_valid(
    milestones: list[RoadmapMilestone],
    catalog_keys: set[str],
    options: RoadmapOptions,
) -> tuple[list[RoadmapMilestone], list[str]]:
    """Drop invalid phases until the roadmap passes validation.

    Repair is deterministic and never fabricates: an offending phase is
    removed (its problems return to the unused pool for no one, because
    generation already happened) and the reason is recorded as a limitation.
    """
    limitations: list[str] = []
    while milestones:
        result = validate_roadmap(milestones, catalog_keys, options)
        if result.valid:
            break
        offending = _first_offending_index(milestones, catalog_keys, options)
        if offending is None:
            break
        removed = milestones.pop(offending)
        limitations.append(
            f"Phase '{removed.title}' was omitted: it could not be filled with "
            f"{options.min_problems_per_phase} verified, unused problems."
        )
    for index, milestone in enumerate(milestones, 1):
        milestone.order = index
        milestone.id = f"phase-{index}"
        milestone.next_milestone_id = (
            f"phase-{index + 1}" if index < len(milestones) else None
        )
        milestone.status = _PHASE_STATUS[min(index - 1, len(_PHASE_STATUS) - 1)]
    return milestones, limitations


def _first_offending_index(
    milestones: Sequence[RoadmapMilestone],
    catalog_keys: set[str],
    options: RoadmapOptions,
) -> int | None:
    seen_keys: set[str] = set()
    seen_titles: set[str] = set()
    for index, milestone in enumerate(milestones):
        problems = milestone.recommended_problems
        if len(problems) < options.min_problems_per_phase:
            return index
        if not milestone.title.strip() or not milestone.learning_objective.strip():
            return index
        if not milestone.relevance.strip():
            return index
        for rec in problems:
            key = (rec.problem_slug or "").strip().lower()
            title_key = canonical_title_key(rec.title)
            if not key or key not in catalog_keys:
                return index
            if key in seen_keys or (title_key and title_key in seen_titles):
                return index
            if not rec.selection_rationale.strip():
                return index
        for rec in problems:
            seen_keys.add((rec.problem_slug or "").strip().lower())
            title_key = canonical_title_key(rec.title)
            if title_key:
                seen_titles.add(title_key)
    return None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def build_roadmap(
    profile: LearningProfile,
    candidates: Sequence[ProblemCandidate],
    options: RoadmapOptions | None = None,
    *,
    evidence_id: str = "",
    evidence_refs: Sequence[str] = (),
) -> PersonalizedRoadmap:
    """Generate a deterministic, validated, deduplicated personalized roadmap."""
    options = options or DEFAULT_ROADMAP_OPTIONS
    catalog_keys = {c.key for c in candidates}
    specs = plan_phase_specs(profile, options)

    used_keys: set[str] = set()
    milestones: list[RoadmapMilestone] = []
    limitations: list[str] = list(profile.limitations)

    for spec in specs:
        phase_seed = _phase_seed(profile, spec)
        ranked = rank_candidates(candidates, phase_seed, options.weights)
        selected = _select_phase_problems(profile, spec, ranked, used_keys, options)
        if not selected:
            limitations.append(
                f"Phase '{spec.title}' was omitted: fewer than "
                f"{options.min_problems_per_phase} verified, unused problems matched it."
            )
            continue

        recommendations = [
            _to_recommendation(item, spec, profile, evidence_refs) for item in selected
        ]
        used_keys.update(item.candidate.key for item in selected)

        prerequisites = spec.prerequisites or (
            ["Basic programming syntax"] if not milestones else []
        )
        milestones.append(
            RoadmapMilestone(
                id=spec.phase_id,
                title=f"Phase {len(milestones) + 1} · {spec.title}",
                order=len(milestones) + 1,
                learning_objective=spec.objective,
                relevance=spec.rationale,
                prerequisites=prerequisites,
                concepts_to_study=spec.target_skills,
                recommended_problems=recommendations,
                completion_criteria=(
                    f"Solve at least {options.min_problems_per_phase} of the "
                    f"{len(recommendations)} problems in this phase and explain the "
                    "pattern and complexity for each."
                ),
                reflection_question=(
                    "Can you explain, without looking it up, when "
                    + (spec.target_skills[0] if spec.target_skills else "this pattern")
                    + " applies and what it costs in time and space?"
                ),
                evidence_refs=list(evidence_refs),
                objective=spec.objective,
                rationale=spec.rationale,
                target_skills=list(spec.target_skills),
                transition="",
            )
        )

    for index, milestone in enumerate(milestones):
        if index < len(milestones) - 1:
            milestone.transition = f"Next: {milestones[index + 1].title}."
        else:
            milestone.transition = "Final phase: consolidate and revisit your revision queue."
        milestone.concepts_to_study = milestone.concepts_to_study or ["General problem solving"]

    milestones, repair_notes = _repair_until_valid(milestones, catalog_keys, options)
    limitations.extend(repair_notes)

    worked = [m for m in milestones if m.recommended_problems]
    if not worked and profile.total_problems == 0:
        limitations.append(
            "No roadmap phases were generated because there are no problems to build on yet."
        )
    elif len(worked) < options.min_phases and worked:
        limitations.append(
            f"Only {len(worked)} phase(s) could be fully populated from the available "
            "verified problems; a larger catalogue or LeetCode problem source would "
            "extend the roadmap."
        )

    early_stage = profile.solved_problems < 3
    description = (
        "An ordered, evidence-based curriculum built from your complete solved and "
        "submission history. Each phase targets a distinct skill and every problem is a "
        "real, verified problem that you have not solved yet."
    )
    if early_stage:
        description = (
            "Early-stage roadmap based on a small history. Treat it as a starting "
            "curriculum rather than a claim about your strengths or weaknesses."
        )

    return PersonalizedRoadmap(
        title="Personalized DSA Learning Roadmap",
        description=description,
        milestones=milestones,
        evidence_id=evidence_id,
        is_read_only=True,
        learning_profile_summary=profile.summary_line(),
        overall_rationale=(
            "Phases move from reinforcing your most recent solve, through patterns with "
            "recorded failures and adjacent techniques, into foundational gaps and "
            "synthesis practice."
        ),
        limitations=limitations,
        is_early_stage=early_stage,
    )
