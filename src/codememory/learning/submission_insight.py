"""Deterministic per-submission learning analysis.

Answers Question B: *"What should I learn from this specific attempt?"*

Distinct from the collective engine: this reasons about one submission, its
recorded metadata, its source code structure, an optional cached deterministic
analysis, and the previous attempt for the same problem.  It never invents a
complexity, a bug, or a comparison that the recorded data does not support.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping, Optional, Sequence

from codememory.ai.models import (
    AttemptComparison,
    OptimizationExplanation,
    SubmissionAnalysis,
    SubmissionImprovement,
    SubmissionLearningAnalysis,
)
from codememory.domain.enums import SubmissionStatus
from codememory.domain.models import Problem, Submission
from codememory.learning.code_signals import complexity_rank, scan_code
from codememory.learning.optimization import build_optimization_explanation

_KNOWN_COMPLEXITY = {"unknown", "", None}


def _status(submission: Submission | None) -> str:
    if submission is None:
        return "Unknown"
    return getattr(submission.status, "value", str(submission.status))


def _is_accepted(submission: Submission | None) -> bool:
    return submission is not None and submission.status == SubmissionStatus.ACCEPTED


def _fmt(value: float | None, unit: str) -> str:
    return f"{value:.1f} {unit}" if value is not None else "not recorded"


def build_submission_learning_analysis(
    problem: Problem,
    submission: Submission,
    *,
    previous_submission: Optional[Submission] = None,
    analysis: Optional[SubmissionAnalysis] = None,
    pattern_history: Optional[Mapping[str, Sequence[str]]] = None,
    evidence_refs: Sequence[str] = (),
) -> SubmissionLearningAnalysis:
    """Build a grounded, structured learning analysis for one submission."""
    refs = [r for r in evidence_refs if r]
    signals = scan_code(submission.code)
    has_code = signals.has_code

    if analysis and analysis.time_complexity and analysis.time_complexity.lower() not in _KNOWN_COMPLEXITY:
        time_c, space_c, source = analysis.time_complexity, analysis.space_complexity, "code_analysis"
        approach = analysis.approach
    elif has_code:
        time_c, space_c, source = (
            signals.estimated_time_complexity,
            signals.estimated_space_complexity,
            "code_estimate",
        )
        approach = ""
    else:
        time_c, space_c, source = "Unknown", "Unknown", "unavailable"
        approach = ""

    optimization = build_optimization_explanation(problem, submission, evidence_refs=refs)
    status = _status(submission)
    topic = problem.topics[0] if problem.topics else "the problem"

    overview = _overview(problem, submission, time_c, space_c, source, signals, optimization)
    what_went_well = _what_went_well(submission, signals, time_c, source, optimization)
    improvements = _improvements(problem, submission, signals, time_c, source, optimization, has_code)
    comparison = _compare(previous_submission, submission, signals, refs)
    connections = _cross_problem_connections(problem, signals, analysis, pattern_history)

    lessons = _lesson(problem, signals, optimization, status)
    next_action = _next_action(submission, signals, optimization)

    limitations: list[str] = []
    if not has_code:
        limitations.append(
            "No source code is stored for this submission, so complexity and structure could not be "
            "derived from the code itself."
        )
    if source == "code_estimate":
        limitations.append(
            "Complexity is a conservative structural estimate from the code text, not a measured value."
        )
    if not comparison.available:
        limitations.append(comparison.summary or "No earlier source submission is available for comparison.")

    return SubmissionLearningAnalysis(
        submission_id=submission.id,
        problem_id=problem.id,
        problem_slug=problem.slug,
        problem_title=problem.title,
        difficulty=str(problem.difficulty.value if hasattr(problem.difficulty, "value") else problem.difficulty),
        topics=list(problem.topics or []),
        status=status,
        language=submission.language or "",
        overview=overview,
        what_went_well=what_went_well,
        improvements=improvements,
        current_approach=approach or optimization.current_approach,
        current_time_complexity=time_c,
        current_space_complexity=space_c,
        complexity_source=source,
        alternative_approach=optimization.recommended_approach,
        alternative_time_complexity=optimization.complexity_comparison.proposed_time,
        alternative_space_complexity=optimization.complexity_comparison.proposed_space,
        tradeoffs=optimization.tradeoffs,
        edge_cases=list(optimization.edge_cases),
        cross_problem_connections=connections,
        previous_attempt_comparison=comparison,
        lesson=lessons,
        next_action=next_action,
        general_pattern=optimization.general_pattern,
        has_code=has_code,
        limitations=limitations,
        evidence_refs=refs,
    )


def _overview(problem, submission, time_c, space_c, source, signals, optimization) -> str:
    status = _status(submission)
    topic = problem.topics[0] if problem.topics else "algorithmic"
    parts = [f"{status} submission for '{problem.title}' ({topic})."]
    if signals.has_code:
        ds = ", ".join(signals.data_structures) if signals.data_structures else "no auxiliary structure detected"
        parts.append(f"Structure: {ds}.")
    label = "estimated" if source == "code_estimate" else "recorded"
    parts.append(f"Complexity ({label}): {time_c} time, {space_c} space.")
    if not _is_accepted(submission):
        parts.append("The attempt did not pass, so correctness takes priority over optimisation.")
    return " ".join(parts)

def _what_went_well(submission, signals, time_c, source, optimization) -> list[str]:
    good: list[str] = []
    if _is_accepted(submission):
        good.append("The submission was accepted, so the algorithm is correct for the tested inputs.")
    if signals.data_structures:
        good.append(
            "Used " + ", ".join(signals.data_structures) + ", an appropriate supporting structure for this approach."
        )
    if signals.has_code and not signals.has_nested_loops:
        good.append(
            "The recorded code contains no nested loops, so the traversal stays linear in the input size."
        )
    if signals.uses_two_pointers:
        good.append("Coordinates two pointers instead of re-scanning the input, which keeps the pass single.")
    if signals.uses_binary_search:
        good.append("Reduces the search space by halving it, giving logarithmic rather than linear search.")
    if not _is_accepted(submission) and _status(submission) == "Time Limit Exceeded":
        good.append("The approach is functionally correct but needs a lower complexity class.")
    if not good:
        good.append("The submission was recorded, giving a concrete baseline to compare future attempts against.")
    return good


def _improvements(problem, submission, signals, time_c, source, optimization, has_code) -> list[SubmissionImprovement]:
    items: list[SubmissionImprovement] = []

    cur_rank = complexity_rank(time_c)
    proposed_label = optimization.complexity_comparison.proposed_time
    prop_rank = complexity_rank(proposed_label)
    # A complexity improvement may only be claimed when the explanation itself
    # asserts one -- the already-optimal branch states "no complexity change".
    has_complexity_change = "no complexity change" not in proposed_label.lower()
    if (
        cur_rank is not None
        and prop_rank is not None
        and prop_rank < cur_rank
        and has_complexity_change
    ):
        items.append(
            SubmissionImprovement(
                title=f"Reduce time from {time_c} to {proposed_label}",
                what=optimization.current_solution_summary or optimization.bottleneck,
                why=optimization.why_it_matters,
                how=" ".join(optimization.transformation_steps[:2])
                or optimization.why_it_works,
                evidence_refs=list(optimization.evidence_refs),
            )
        )
    elif has_code and cur_rank is not None:
        items.append(
            SubmissionImprovement(
                title="Tighten constants and auxiliary memory",
                what=optimization.bottleneck,
                why=optimization.why_it_matters,
                how=optimization.why_it_works,
                evidence_refs=list(optimization.evidence_refs),
            )
        )

    if not _is_accepted(submission):
        items.append(
            SubmissionImprovement(
                title="Re-establish correctness before optimising",
                what=f"The recorded verdict was '{_status(submission)}'.",
                why="An incorrect solution cannot be judged on efficiency.",
                how=(
                    "Re-derive the algorithm's invariant and test the empty, single-element and "
                    "duplicate cases explicitly."
                ),
                evidence_refs=list(optimization.evidence_refs),
            )
        )

    for case in optimization.edge_cases[:2]:
        items.append(
            SubmissionImprovement(
                title=f"Verify edge case: {case}",
                what=f"'{case}' can change the correct output for {problem.title}.",
                why="Untested boundaries are the most common source of wrong answers on hidden tests.",
                how=f"Add a small explicit test for '{case}' and confirm the branch behaves as intended.",
                evidence_refs=[],
            )
        )

    if signals.uses_hash_map and signals.has_code and cur_rank is not None and cur_rank >= 3:
        items.append(
            SubmissionImprovement(
                title="Check whether the auxiliary structure is necessary",
                what=f"The code stores intermediate state ({', '.join(signals.data_structures)}).",
                why="Auxiliary memory is a real cost when the constraint is tight.",
                how="Confirm the structure is required for correctness; if it is only for convenience, replace it with a running variable.",
                evidence_refs=[],
            )
        )
    return items


def _compare(previous, current, signals, refs) -> AttemptComparison:
    if previous is None:
        return AttemptComparison(
            available=False,
            summary="No earlier submission is recorded for this problem.",
            evidence_refs=refs,
        )
    prev_has_code = bool(previous.code and previous.code.strip())
    if not prev_has_code:
        return AttemptComparison(
            available=False,
            previous_submission_id=previous.id,
            previous_status=_status(previous),
            current_status=_status(current),
            summary="No earlier source submission is available for comparison.",
            evidence_refs=refs,
        )

    prev_signals = scan_code(previous.code)
    changes: list[str] = []
    if _status(previous) != _status(current):
        changes.append(f"Verdict changed from {_status(previous)} to {_status(current)}.")
    if prev_signals.has_nested_loops and not signals.has_nested_loops:
        changes.append("Nested iteration in the earlier attempt was removed in this attempt.")
    if not prev_signals.data_structures and signals.data_structures:
        changes.append("Introduced " + ", ".join(signals.data_structures) + ".")
    if previous.runtime_ms is not None and current.runtime_ms is not None:
        delta = current.runtime_ms - previous.runtime_ms
        if abs(delta) >= 1.0:
            changes.append(
                f"Runtime {'improved' if delta < 0 else 'increased'} by {abs(delta):.1f} ms "
                f"({_fmt(previous.runtime_ms, 'ms')} -> {_fmt(current.runtime_ms, 'ms')})."
            )
    if previous.memory_mb is not None and current.memory_mb is not None:
        delta = current.memory_mb - previous.memory_mb
        if abs(delta) >= 0.1:
            changes.append(
                f"Memory {'dropped' if delta < 0 else 'grew'} by {abs(delta):.1f} MB "
                f"({_fmt(previous.memory_mb, 'MB')} -> {_fmt(current.memory_mb, 'MB')})."
            )
    if not changes:
        changes.append("No structural change was detected between the two attempts.")

    improvement = ""
    if _is_accepted(current) and not _is_accepted(previous):
        improvement = f"Resolved the previous '{_status(previous)}' verdict."
    elif not _is_accepted(previous) and not _is_accepted(current):
        improvement = "Still not accepted; the failing factor remains unresolved."

    lesson = (
        "Compare what changed between the two attempts and keep the change that actually moved the verdict."
    )
    return AttemptComparison(
        available=True,
        previous_submission_id=previous.id,
        previous_status=_status(previous),
        current_status=_status(current),
        summary=" ".join(changes),
        changes=changes,
        improvement=improvement,
        lesson=lesson,
        evidence_refs=refs,
    )


def _cross_problem_connections(problem, signals, analysis, pattern_history) -> list[str]:
    if not pattern_history:
        return []
    labels: list[str] = []
    for ds in signals.data_structures:
        labels.append(ds)
    if signals.uses_two_pointers:
        labels.append("Two Pointers")
    if signals.uses_binary_search:
        labels.append("Binary Search")
    if signals.uses_memoization:
        labels.append("Dynamic Programming / Memoization")

    connections: list[str] = []
    for label in dict.fromkeys(labels):
        others = [t for t in pattern_history.get(label, []) if t != problem.title]
        if others:
            connections.append(
                f"This submission uses {label}, the same pattern you applied in: "
                + ", ".join(others[:3])
                + "."
            )
    return connections[:3]


def _lesson(problem, signals, optimization, status) -> str:
    if optimization.general_pattern:
        return optimization.general_pattern
    if signals.has_nested_loops:
        return "Nested iteration is a signal to check whether an inner lookup can be made constant-time."
    if signals.uses_hash_map:
        return "Recognise constant-time lookup problems as a hash-map pattern."
    return f"Record the invariant you relied on for '{problem.title}' so it transfers to similar problems."


def _next_action(submission, signals, optimization) -> str:
    if not _is_accepted(submission):
        return "Fix the failing behaviour, then re-submit and compare the new attempt against this one."
    if signals.has_nested_loops:
        return "Re-implement with the inner search removed and confirm the complexity drops."
    return "Move to a harder problem in the same topic, or apply this pattern in a combined-topic problem."
