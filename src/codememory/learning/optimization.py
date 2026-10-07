"""Deterministic, evidence-honest optimization explanations.

An optimization may only be claimed when the recorded source code supports it.
When the code is unavailable, or when no asymptotic bottleneck can be derived
from it, the explanation says so plainly instead of inventing one.
"""

from __future__ import annotations

import re
from typing import Optional, Sequence

from codememory.ai.models import ComplexityComparison, OptimizationExplanation
from codememory.domain.models import Problem, Submission

# Topics where nested iteration is inherent to the solution shape; labelling
# them "brute force" would be factually wrong.
_MULTI_LOOP_TOPICS = {
    "Dynamic Programming",
    "Tree",
    "Binary Tree",
    "Graph",
    "Depth-First Search",
    "Breadth-First Search",
    "Backtracking",
    "Matrix",
    "Trie",
    "Segment Tree",
    "Heap (Priority Queue)",
}

_EDGE_CASES_BY_TOPIC = {
    "Array": ["Empty input", "Single element", "All elements equal", "Negative numbers"],
    "Hash Table": ["Duplicate keys", "Empty input", "Hash collisions (worst case)"],
    "Two Pointers": ["Fewer than two elements", "All elements equal", "Unsorted input"],
    "Sliding Window": ["Empty input", "Window larger than input", "All negative values"],
    "Binary Search": ["Empty array", "Target smaller/larger than all elements", "Duplicate targets"],
    "String": ["Empty string", "Single character", "Repeated characters", "Case sensitivity"],
    "Linked List": ["Empty list", "Single node", "Cycle present", "Duplicate values"],
    "Tree": ["Empty tree", "Single node", "Skewed tree", "Duplicate values"],
    "Binary Tree": ["Empty tree", "Single node", "Skewed tree", "Duplicate values"],
    "Graph": ["Disconnected components", "Self-loops", "Cycles", "Empty graph"],
    "Dynamic Programming": ["Empty input", "Base cases", "Integer overflow on large n"],
    "Stack": ["Empty stack pop", "All elements pushed then popped", "Nested structures"],
    "Heap (Priority Queue)": ["Empty heap", "All elements equal", "Single element"],
}


def _edge_cases_for(topics: Sequence[str]) -> list[str]:
    cases: list[str] = []
    for topic in topics:
        for case in _EDGE_CASES_BY_TOPIC.get(topic, []):
            if case not in cases:
                cases.append(case)
    if not cases:
        cases = ["Empty input", "Single element", "Duplicate elements"]
    return cases[:5]


def _primary_topic(problem: Problem) -> str:
    return problem.topics[0] if problem.topics else "Algorithmic Problem"


def _status_value(submission: Optional[Submission]) -> str:
    if submission is None:
        return "Attempt"
    return getattr(submission.status, "value", str(submission.status))


def build_optimization_explanation(
    problem: Problem,
    submission: Optional[Submission],
    *,
    evidence_refs: Sequence[str] = (),
) -> OptimizationExplanation:
    """Build a grounded optimization explanation for a submission."""
    refs = list(evidence_refs)
    code = submission.code if (submission and submission.code) else ""
    code_lower = code.lower()
    has_code = bool(code.strip())
    topics = list(problem.topics or [])
    topics_str = ", ".join(topics) if topics else _primary_topic(problem)
    primary_topic = _primary_topic(problem)
    approach_source = "code_analysis" if has_code else "metadata"

    if not has_code:
        summary = (
            f"No source code was stored for this submission of '{problem.title}'. "
            "The analysis below is derived from recorded metadata only."
        )
        return OptimizationExplanation(
            problem_slug=problem.slug,
            submission_id=submission.id if submission else None,
            current_approach=f"Recorded attempt ({topics_str})",
            approach_source=approach_source,
            current_solution_summary=summary,
            bottleneck=(
                "Cannot be determined: the submission's source code is not available, so no "
                "complexity claim can be made from evidence."
            ),
            why_it_matters=(
                "Without the code, efficiency cannot be assessed. Import or sync submissions "
                "with their source to receive a concrete optimization analysis."
            ),
            recommended_approach=f"Re-solve and record a {primary_topic} solution with code",
            why_it_works=(
                "Recording the source lets CodeMemory derive the actual complexity and compare "
                "it against an improved approach."
            ),
            complexity_comparison=ComplexityComparison(
                current_time="Unknown [Estimated - no code]",
                proposed_time="Unknown [Estimated - no code]",
                current_space="Unknown [Estimated - no code]",
                proposed_space="Unknown [Estimated - no code]",
                explanation="No complexity comparison is possible without source code.",
                assumptions="None; no code was available.",
            ),
            transformation_steps=[],
            tradeoffs="Not assessable without source code.",
            worked_example=None,
            edge_cases=_edge_cases_for(topics),
            when_original_is_acceptable="Not assessable without source code.",
            takeaway=(
                "Store the submission's source code so CodeMemory can analyse approach, "
                "complexity, and concrete improvements."
            ),
            general_pattern=f"Recorded {primary_topic} attempt (no code to analyse)",
            follow_up_question="Can you re-import this submission with its source code?",
            evidence_refs=refs,
        )

    for_count = len(re.findall(r"\bfor\b", code_lower))
    while_count = len(re.findall(r"\bwhile\b", code_lower))
    has_nested = bool(re.search(r"for[^\n]*\n(?:[^\n]*\n){0,3}[^\n]*for", code)) or bool(
        re.search(r"while[^\n]*\n(?:[^\n]*\n){0,3}[^\n]*while", code)
    )
    topic_permits_nested = any(t in _MULTI_LOOP_TOPICS for t in topics)
    accepted = _status_value(submission) == "Accepted"

    summary = (
        f"The recorded solution for '{problem.title}' is written in "
        f"{(submission.language if submission else 'unknown')} and contains "
        f"{for_count} for-loop(s) and {while_count} while-loop(s)."
    )

    if has_nested and not topic_permits_nested:
        current_approach = f"Iterative pairwise comparison ({topics_str})"
        bottleneck = (
            "The solution nests an iteration inside another iteration, so for each element it "
            "re-scans part of the remaining input. When both loops span the input, the work "
            "grows quadratically and the solution times out on large inputs."
        )
        why_it_matters = (
            "Quadratic work is the most common cause of Time Limit Exceeded. Replacing the inner "
            "scan with a constant-time lookup collapses the problem to a single pass."
        )
        recommended_approach = f"Single-pass lookup using a hash table ({primary_topic})"
        why_works = (
            "For each element x the required counterpart can be computed directly (for example "
            "target - x). A hash map records values already seen, so the lookup costs O(1) on "
            "average instead of a scan. Every element is therefore examined once."
        )
        comparison = ComplexityComparison(
            current_time="O(n^2)",
            proposed_time="O(n)",
            current_space="O(1)",
            proposed_space="O(n)",
            explanation=(
                "The nested search performs up to n comparisons for each of n elements; the hash "
                "map replaces that inner search with an average O(1) lookup."
            ),
            assumptions="Average-case hash table behaviour; the counterpart must be computable in O(1).",
        )
        steps = [
            "Identify the value the inner loop is searching for on each iteration.",
            "Express that value as a function of the current element (the complement).",
            "Create a hash map before the loop to record values already visited.",
            "Replace the inner loop with one hash-map lookup for the complement.",
            "Insert the current element into the map and continue the single pass.",
        ]
        tradeoffs = (
            "Adds O(n) auxiliary memory to hold the lookup structure in exchange for removing a "
            "factor of n in time. If memory is strictly bounded, the quadratic version is the "
            "fallback."
        )
        when_ok = (
            "The nested version remains acceptable for tiny inputs or when the input is bounded "
            "by a small constant, but it will not scale."
        )
        general_pattern = (
            "Replace repeated searching with a lookup structure: turn an O(n) inner search into "
            "an O(1) average lookup using a hash map."
        )
        worked = (
            "On the first pass, store each visited value with its index, then check whether the "
            "required complement is already stored; if it is, return the pair immediately."
        )
        takeaway = (
            "When an inner loop is searching for a specific value, ask whether that value can be "
            "looked up instead of searched."
        )
    elif has_nested and topic_permits_nested:
        current_approach = f"Nested traversal expected for {primary_topic} ({topics_str})"
        bottleneck = (
            f"Nested iteration is intrinsic to {primary_topic}, so the nesting itself is not the "
            "problem. Any improvement comes from reducing redundant state or recomputation, not "
            "from removing the loops."
        )
        why_it_matters = (
            "Optimising the wrong dimension wastes effort. For this pattern, total work follows "
            "the traversal structure, so gains come from memoisation or space reduction."
        )
        recommended_approach = f"{primary_topic} with reduced state (memoisation or rolling arrays)"
        why_works = (
            "Many nested-traversal solutions recompute states that were already known. Caching "
            "those states (or rolling the working set from O(n^2) to O(n)) removes duplicated work."
        )
        comparison = ComplexityComparison(
            current_time="Depends on the traversal (often O(n*m))",
            proposed_time="Same order, with removed recomputation",
            current_space="O(n) or O(n*m) state",
            proposed_space="Potentially O(n) or O(1) with a rolling structure",
            explanation=(
                "The traversal order is inherent; the improvement target is redundant "
                "recomputation and auxiliary state, verified against the actual recurrence."
            ),
            assumptions="The recurrence only depends on the previous layer/row.",
        )
        steps = [
            "Write down what the inner iteration recomputes on each step.",
            "Check whether that value depends only on previously computed state.",
            "Cache the state (memoisation) or keep only the last layer (rolling array).",
            "Re-run against edge cases to confirm the reduced state is sufficient.",
        ]
        tradeoffs = (
            "Memoisation trades memory for time; rolling arrays trade clarity for memory. Both "
            "must be re-verified against the base cases."
        )
        when_ok = (
            "If the input is small or the recurrence is not repeated, the straightforward nested "
            "version is clearer and perfectly acceptable."
        )
        general_pattern = (
            "In nested-traversal patterns, optimise redundant state and recomputation rather than "
            "the loop nesting itself."
        )
        worked = (
            "If only the previous row of a table is needed, keep two rows instead of the full "
            "matrix and drop the space by a factor of n."
        )
        takeaway = (
            "Match the optimisation to the pattern: not every nested loop is a brute-force "
            "solution waiting to be collapsed."
        )
    else:
        current_approach = f"Single-pass / linear approach ({topics_str})"
        bottleneck = (
            "No asymptotic bottleneck is derivable from the recorded code: it does not contain "
            "nested iteration, so its worst-case time is linear in the input. Any remaining gain "
            "would be constant-factor, not a change of complexity class."
        )
        why_it_matters = (
            "Claiming an optimization that the code does not support would be misleading. The "
            "honest improvement here is correctness, clarity, and constant-factor tightness."
        )
        recommended_approach = f"Verified {primary_topic} single-pass solution"
        why_works = (
            "The solution already visits each element a bounded number of times. Gains come from "
            "removing unnecessary allocations, redundant passes, or extra data structures."
        )
        comparison = ComplexityComparison(
            current_time="O(n)",
            proposed_time="O(n) (no complexity change derivable)",
            current_space="O(1) or O(n) depending on structures used",
            proposed_space="Potentially O(1) if auxiliary state can be eliminated",
            explanation=(
                "No change of complexity class can be justified from the recorded code; only "
                "constant-factor or space improvements may apply."
            ),
            assumptions="The stated complexity reflects the recorded code structure.",
        )
        steps = [
            "Confirm the single pass cannot be restructured into a cheaper operation.",
            "Check whether any auxiliary structure can be removed or reused.",
            "Verify boundary handling for empty, single-element, and duplicate inputs.",
            "Re-measure runtime at the largest input bound if available.",
        ]
        tradeoffs = (
            "Removing an auxiliary structure may reduce clarity; keeping it may cost memory. "
            "Choose based on which constraint actually binds."
        )
        when_ok = (
            "A linear solution with acceptable constants is the target for most problems; this "
            "version is already asymptotically appropriate."
        )
        general_pattern = (
            "Distinguish a genuine complexity bottleneck from constant-factor tuning before "
            "changing an already-linear solution."
        )
        worked = (
            "If a set or counter is only ever read within the same loop, check whether a running "
            "variable can replace it and drop the allocation."
        )
        takeaway = (
            "Not every solution needs a faster algorithm. Verify the bottleneck before optimising."
        )

    submission_note = "" if accepted else (
        f" The recorded verdict for this submission was '{_status_value(submission)}', so "
        "correctness should be re-established before optimising further."
    )

    return OptimizationExplanation(
        problem_slug=problem.slug,
        submission_id=submission.id if submission else None,
        current_approach=current_approach,
        approach_source=approach_source,
        current_solution_summary=summary + submission_note,
        bottleneck=bottleneck,
        why_it_matters=why_it_matters,
        recommended_approach=recommended_approach,
        why_it_works=why_works,
        complexity_comparison=comparison,
        transformation_steps=steps,
        tradeoffs=tradeoffs,
        worked_example=worked,
        edge_cases=_edge_cases_for(topics),
        when_original_is_acceptable=when_ok,
        takeaway=takeaway,
        general_pattern=general_pattern,
        follow_up_question=(
            "How would your approach change if memory were constrained to O(1)?"
        ),
        evidence_refs=refs,
    )
