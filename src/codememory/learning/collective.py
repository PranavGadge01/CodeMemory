"""Deterministic collective learning insight engine.

Answers Question A: *"What have I learned from solving all these problems?"*

Everything here is computed from recorded CodeMemory data -- analytics metrics,
pattern analysis, stored submissions and their cached deterministic analyses.
No language model participates in producing the facts, the patterns, or the
prioritisation; a provider may only rephrase the already-structured findings.

Each emitted insight item declares which level of the evidence hierarchy it
belongs to (fact / pattern / interpretation / action) and carries the evidence
IDs it was derived from, so interpretations are never shown as facts.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping, Optional, Sequence

from codememory.ai.evidence_models import EvidenceItem, InsightEvidence, _make_evidence_id
from codememory.ai.models import (
    CollectiveLearningInsight,
    CollectiveLearningProfile,
    LearningInsightItem,
    LearningProgressTrend,
    SubmissionAnalysis,
)
from codememory.domain.enums import SubmissionStatus
from codememory.domain.models import Attempt, Problem, Submission
from codememory.learning.code_signals import CodeSignals, complexity_rank, scan_code
from codememory.learning.taxonomy import TOPIC_TO_PATTERNS, is_foundational, patterns_for_topics

_MIN_TOPIC_PROBLEMS = 2
_EARLY_STAGE_PROBLEMS = 3
_PROGRESS_MIN_SUBMISSIONS = 6
_MAX_ITEMS = 5


@dataclass
class _SubmissionRecord:
    problem: Problem
    submission: Submission
    attempt: Attempt
    attempt_number: int
    order: int
    analysis: Optional[SubmissionAnalysis]
    signals: CodeSignals
    time_complexity: str
    space_complexity: str
    complexity_source: str


def _resolve_complexity(
    submission: Submission,
    attempt: Attempt,
    analysis: Optional[SubmissionAnalysis],
    signals: CodeSignals,
) -> tuple[str, str, str]:
    """Choose the most reliable complexity label available for a submission.

    Preference order: cached deterministic analysis > stored attempt analysis >
    conservative structural estimate from the code.  The source is returned so
    the UI can label estimates honestly.
    """
    if analysis and analysis.time_complexity and analysis.time_complexity.lower() != "unknown":
        return analysis.time_complexity, analysis.space_complexity, "code_analysis"
    if attempt.analysis and attempt.analysis.time_complexity:
        return attempt.analysis.time_complexity, attempt.analysis.space_complexity, "attempt_analysis"
    if signals.has_code:
        return signals.estimated_time_complexity, signals.estimated_space_complexity, "code_estimate"
    return "Unknown", "Unknown", "unavailable"


def _collect_submissions(
    problems: Sequence[Problem],
    analyses: Mapping[str, SubmissionAnalysis] | None,
) -> list[_SubmissionRecord]:
    """Flatten every stored submission into one deterministic, time-ordered list."""
    records: list[_SubmissionRecord] = []
    order = 0
    for problem in problems:
        pairs: list[tuple[Attempt, Submission]] = []
        for attempt in problem.attempts:
            for sub in attempt.submissions:
                pairs.append((attempt, sub))
        pairs.sort(key=lambda p: p[1].submitted_at or datetime.min.replace(tzinfo=timezone.utc))
        for attempt_number, (attempt, sub) in enumerate(pairs, start=1):
            analysis = analyses.get(sub.id) if analyses else None
            signals = scan_code(sub.code)
            time_c, space_c, source = _resolve_complexity(sub, attempt, analysis, signals)
            records.append(
                _SubmissionRecord(
                    problem=problem,
                    submission=sub,
                    attempt=attempt,
                    attempt_number=attempt_number,
                    order=order,
                    analysis=analysis,
                    signals=signals,
                    time_complexity=time_c,
                    space_complexity=space_c,
                    complexity_source=source,
                )
            )
            order += 1
    records.sort(key=lambda r: (r.submission.submitted_at or datetime.min.replace(tzinfo=timezone.utc), r.order))
    return records


def _is_accepted(submission: Submission) -> bool:
    return submission.status == SubmissionStatus.ACCEPTED


def _topic_key(topic: str) -> str:
    return topic.lower().replace(" ", "_").replace("-", "_")


class _EvidenceWriter:
    """Appends deterministic evidence items and returns only valid refs."""

    def __init__(self, evidence: InsightEvidence) -> None:
        self.evidence = evidence
        self._existing = set(evidence.all_evidence_ids())

    def add(self, eid: str, source: str, label: str, value, **kwargs) -> str:
        if eid not in self._existing:
            self.evidence.items.append(
                EvidenceItem(
                    evidence_id=eid,
                    source=source,
                    source_type="deterministic",
                    label=label,
                    value=value,
                    **kwargs,
                )
            )
            self._existing.add(eid)
        return eid

    def ref(self, eid: str) -> str | None:
        return eid if eid in self._existing else None
    def refs(self, *eids: str) -> list[str]:
        return [e for e in eids if e and e in self._existing]


def build_collective_learning_insight(
    evidence: InsightEvidence,
    problems: Sequence[Problem],
    analyses: Mapping[str, SubmissionAnalysis] | None = None,
) -> CollectiveLearningInsight:
    """Build the structured, evidence-backed collective learning insight."""
    writer = _EvidenceWriter(evidence)
    records = _collect_submissions(problems, analyses)

    overview = evidence.metrics.overview or {}
    total_problems = int(overview.get("total_problems", 0) or 0)
    total_submissions = int(overview.get("total_submissions", 0) or 0)

    profile = _build_profile(evidence, problems, records)
    strengths = _detect_strengths(evidence, records, profile, writer)
    unpracticed = _detect_unpracticed(evidence, writer)
    weaknesses, struggles = _detect_weaknesses(evidence, records, profile, writer)
    mistakes = _detect_recurring_mistakes(records, writer)
    trends = _detect_optimization_trends(records, writer)
    progress = _detect_progress(evidence, records, writer)
    focus_areas = _rank_focus_areas(unpracticed, struggles, mistakes)

    limitations = list(evidence.limitations)
    if total_problems == 0:
        limitations.append("No problems recorded yet; nothing can be said about strengths or weaknesses.")
    elif total_problems < _EARLY_STAGE_PROBLEMS:
        limitations.append(
            f"Only {total_problems} problem(s) recorded; this profile is preliminary and may change."
        )
    if records and not any(r.analysis for r in records):
        limitations.append(
            "No cached code analyses were available; complexity signals come from structural estimates."
        )

    summary = _build_summary(profile, strengths, weaknesses, trends)
    actions = _build_actions(focus_areas, mistakes, trends)

    return CollectiveLearningInsight(
        scope="full_profile",
        generated_at=evidence.generated_at,
        overall_summary=summary,
        profile=profile,
        strengths=strengths[:_MAX_ITEMS],
        weaknesses=weaknesses[:_MAX_ITEMS],
        recurring_mistakes=mistakes[:_MAX_ITEMS],
        optimization_trends=trends[:_MAX_ITEMS],
        progress=progress[:_MAX_ITEMS],
        focus_areas=focus_areas[:_MAX_ITEMS],
        recommended_actions=actions[:_MAX_ITEMS],
        limitations=limitations,
        is_early_stage=total_problems < _EARLY_STAGE_PROBLEMS or total_submissions < 3,
        evidence_id=evidence.evidence_id,
        evidence_refs=sorted(evidence.all_evidence_ids()),
    )


def _build_profile(
    evidence: InsightEvidence,
    problems: Sequence[Problem],
    records: Sequence[_SubmissionRecord],
) -> CollectiveLearningProfile:
    overview = evidence.metrics.overview or {}
    difficulty_stats = evidence.metrics.difficulty_stats or []
    topic_stats = evidence.metrics.topic_stats or []

    difficulty_solved = {
        str(ds.get("difficulty", "Unknown")): int(ds.get("solved_problems", 0) or 0)
        for ds in difficulty_stats
    }

    solved_patterns: Counter[str] = Counter()
    for problem in problems:
        if problem.latest_accepted_submission is not None:
            for pattern in patterns_for_topics(list(problem.topics or [])):
                solved_patterns[pattern] += 1

    lang_counter: Counter[str] = Counter()
    for rec in records:
        if rec.submission.language:
            lang_counter[rec.submission.language] += 1
    total_lang = sum(lang_counter.values()) or 1
    language_share = [
        {"language": lang, "submissions": count, "share_pct": round(count / total_lang * 100, 1)}
        for lang, count in lang_counter.most_common()
    ]

    complexity_signals = [
        {
            "problem_slug": rec.problem.slug,
            "submission_id": rec.submission.id,
            "time_complexity": rec.time_complexity,
            "space_complexity": rec.space_complexity,
            "source": rec.complexity_source,
        }
        for rec in records
        if rec.complexity_source != "unavailable"
    ]

    return CollectiveLearningProfile(
        total_problems=int(overview.get("total_problems", 0) or 0),
        total_attempted=int(overview.get("total_problems", 0) or 0),
        total_solved=int(overview.get("accepted_problems", 0) or 0),
        total_submissions=int(overview.get("total_submissions", 0) or 0),
        total_attempts=int(overview.get("total_attempts", 0) or 0),
        acceptance_rate_pct=round(float(overview.get("overall_acceptance_rate_pct", 0.0) or 0.0), 1),
        first_attempt_acceptance_rate_pct=round(
            float(overview.get("first_attempt_acceptance_rate_pct", 0.0) or 0.0), 1
        ),
        avg_attempts_per_solved_problem=round(
            float(overview.get("avg_attempts_per_solved_problem", 0.0) or 0.0), 2
        ),
        difficulty_solved=difficulty_solved,
        topic_observations=[dict(ts) for ts in topic_stats],
        language_share=language_share,
        patterns_practiced=sorted(pattern for pattern, n in solved_patterns.items() if n >= 1),
        complexity_signals=complexity_signals,
    )

def _detect_strengths(
    evidence: InsightEvidence,
    records: Sequence[_SubmissionRecord],
    profile: CollectiveLearningProfile,
    writer: _EvidenceWriter,
) -> list[LearningInsightItem]:
    strengths: list[LearningInsightItem] = []

    for ts in evidence.metrics.topic_stats:
        topic = str(ts.get("topic", "?"))
        solved = int(ts.get("solved_problems", 0) or 0)
        total = int(ts.get("total_problems", 0) or 0)
        success = float(ts.get("success_rate_pct", 0.0) or 0.0)
        if total < _MIN_TOPIC_PROBLEMS or solved < 2 or success < 60.0:
            continue
        key = _topic_key(topic)
        ref = writer.add(
            _make_evidence_id("collective", "strength", "topic", key),
            f"collective.strength.topic.{key}",
            f"{topic} solving strength",
            {"solved": solved, "total": total, "success_rate_pct": success},
        )
        confidence = "recurring" if total >= 3 else "early_signal"
        strengths.append(
            LearningInsightItem(
                category="fact",
                title=f"{topic} problem solving",
                summary=(
                    f"Solved {solved} of {total} {topic} problems with a {success:.0f}% "
                    "problem-level success rate."
                ),
                evidence=f"Recorded {total} {topic} problem(s); {solved} solved.",
                impact=(
                    f"Demonstrates working familiarity with {topic} rather than a single lucky solve."
                ),
                interpretation=(
                    "Demonstrated strength supported by multiple accepted solutions."
                    if confidence == "recurring"
                    else "Early signal: only a small number of problems support this strength so far."
                ),
                action=f"Next level: apply {topic} in a harder or combined-topic problem.",
                priority="high" if solved >= 4 else "medium",
                confidence=confidence,
                topics=[topic],
                evidence_refs=writer.refs(ref),
            )
        )

    pattern_examples: dict[str, list[str]] = defaultdict(list)
    for rec in records:
        if not _is_accepted(rec.submission):
            continue
        for label in _patterns_in_record(rec):
            if rec.problem.title not in pattern_examples[label]:
                pattern_examples[label].append(rec.problem.title)
    for label, examples in pattern_examples.items():
        if len(examples) < 2:
            continue
        key = label.lower().replace(" ", "_").replace("/", "_")
        ref = writer.add(
            _make_evidence_id("collective", "strength", "pattern", key),
            f"collective.strength.pattern.{key}",
            f"Accepted solutions using {label}",
            {"count": len(examples), "examples": examples},
        )
        strengths.append(
            LearningInsightItem(
                category="fact",
                title=f"Applied {label} successfully",
                summary=f"Accepted solutions across {len(examples)} problems use {label}.",
                evidence="Representative problems: " + ", ".join(examples[:4]) + ".",
                impact=f"Shows {label} is part of the working toolkit, not an isolated experiment.",
                interpretation="Recurring, demonstrated technique.",
                action=f"Next level: reach for {label} earlier, before the obvious brute-force approach.",
                priority="medium",
                confidence="recurring" if len(examples) >= 3 else "early_signal",
                examples=examples[:4],
                evidence_refs=writer.refs(ref),
            )
        )

    solved_medium = sum(n for d, n in profile.difficulty_solved.items() if d.lower().startswith("med"))
    solved_hard = sum(n for d, n in profile.difficulty_solved.items() if d.lower().startswith("hard"))
    if solved_medium >= 2 or solved_hard >= 1:
        diff_detail = f"{solved_medium} Medium" + (f", {solved_hard} Hard" if solved_hard else "")
        ref = writer.add(
            _make_evidence_id("collective", "strength", "difficulty"),
            "collective.strength.difficulty",
            "Solved Medium/Hard problems",
            {"medium": solved_medium, "hard": solved_hard},
        )
        strengths.append(
            LearningInsightItem(
                category="fact",
                title="Progress beyond Easy problems",
                summary=f"Solved {diff_detail} problem(s).",
                evidence=f"Solved difficulty distribution: {profile.difficulty_solved}.",
                impact="Shows the difficulty ceiling is rising rather than staying at Easy.",
                interpretation="Demonstrated ability to clear harder problems.",
                action="Next level: attempt one problem above your current comfort difficulty.",
                priority="medium",
                confidence="recurring" if (solved_medium + solved_hard) >= 3 else "early_signal",
                evidence_refs=writer.refs(ref),
            )
        )

    if profile.first_attempt_acceptance_rate_pct >= 60.0 and profile.total_solved >= 3:
        ref = writer.ref(_make_evidence_id("analytics", "overview", "first_attempt_acceptance_rate_pct"))
        strengths.append(
            LearningInsightItem(
                category="fact",
                title="Strong first-attempt accuracy",
                summary=(
                    f"{profile.first_attempt_acceptance_rate_pct:.0f}% of problems were accepted on "
                    "the first attempt."
                ),
                evidence="Derived from recorded first-attempt outcomes.",
                impact="Indicates the initial approach is often correct, not trial-and-error.",
                interpretation="Demonstrated correctness habit.",
                action="Next level: keep first-attempt accuracy while raising problem difficulty.",
                priority="medium",
                confidence="recurring" if profile.total_solved >= 5 else "early_signal",
                evidence_refs=writer.refs(ref or ""),
            )
        )

    strengths.sort(
        key=lambda i: ({"high": 0, "medium": 1, "low": 2}[i.priority], 0 if i.confidence == "recurring" else 1)
    )
    return strengths


def _patterns_in_record(rec: _SubmissionRecord) -> list[str]:
    """Deterministic human labels for a submission's demonstrated technique."""
    labels: list[str] = []
    if rec.analysis:
        labels.extend(a for a in (rec.analysis.algorithms or []) if a)
        labels.extend(d for d in (rec.analysis.data_structures or []) if d)
    for ds in rec.signals.data_structures:
        if ds not in labels:
            labels.append(ds)
    if rec.signals.uses_two_pointers:
        labels.append("Two Pointers")
    if rec.signals.uses_binary_search:
        labels.append("Binary Search")
    if rec.signals.uses_sort:
        labels.append("Sorting")
    if rec.signals.uses_memoization:
        labels.append("Dynamic Programming / Memoization")
    if rec.signals.uses_recursion:
        labels.append("Recursion")
    return list(dict.fromkeys(labels))

def _detect_unpracticed(
    evidence: InsightEvidence,
    writer: _EvidenceWriter,
) -> list[LearningInsightItem]:
    """Topics with zero recorded exposure -- explicitly NOT weaknesses."""
    practiced = {
        str(ts.get("topic", "")).strip().lower()
        for ts in evidence.metrics.topic_stats
        if int(ts.get("total_problems", 0) or 0) > 0
    }
    missing = [topic for topic in TOPIC_TO_PATTERNS if topic.strip().lower() not in practiced]
    if not missing:
        return []

    foundational = [t for t in missing if any(is_foundational(p) for p in TOPIC_TO_PATTERNS.get(t, ()))]
    ordered = foundational + [t for t in missing if t not in foundational]
    ref = writer.add(
        _make_evidence_id("collective", "unpracticed", "topics"),
        "collective.unpracticed.topics",
        "Unpracticed topics",
        missing,
    )
    items: list[LearningInsightItem] = []
    for topic in ordered[:3]:
        items.append(
            LearningInsightItem(
                category="fact",
                title=f"{topic}: not practiced yet",
                summary=f"No {topic} problems are recorded in your history.",
                evidence="Recorded topics: " + (", ".join(sorted(practiced)) if practiced else "none"),
                impact="This is an exposure gap, not a demonstrated weakness -- there is simply no evidence yet.",
                interpretation="Unpracticed area (distinct from a struggle).",
                action=f"Schedule an initial {topic} problem to establish a baseline.",
                priority="high" if topic in foundational else "medium",
                confidence="early_signal",
                topics=[topic],
                evidence_refs=writer.refs(ref),
            )
        )
    return items


def _detect_weaknesses(
    evidence: InsightEvidence,
    records: Sequence[_SubmissionRecord],
    profile: CollectiveLearningProfile,
    writer: _EvidenceWriter,
) -> tuple[list[LearningInsightItem], list[LearningInsightItem]]:
    """Return (weakness items, struggle signals reused for focus ranking)."""
    weaknesses: list[LearningInsightItem] = []
    struggles: list[LearningInsightItem] = []

    for ts in evidence.metrics.topic_stats:
        topic = str(ts.get("topic", "?"))
        total = int(ts.get("total_problems", 0) or 0)
        solved = int(ts.get("solved_problems", 0) or 0)
        submissions = int(ts.get("total_submissions", 0) or 0)
        success = float(ts.get("success_rate_pct", 0.0) or 0.0)
        acceptance = float(ts.get("acceptance_rate_pct", 0.0) or 0.0)
        if total < _MIN_TOPIC_PROBLEMS:
            continue
        key = _topic_key(topic)
        acc_ref = writer.ref(_make_evidence_id("analytics", "topic_stats", key, "acceptance_rate"))
        suc_ref = writer.ref(_make_evidence_id("analytics", "topic_stats", key, "success_rate"))

        if success < 50.0:
            ref = writer.add(
                _make_evidence_id("collective", "weakness", "topic", key),
                f"collective.weakness.topic.{key}",
                f"Low {topic} success rate",
                {"solved": solved, "total": total, "success_rate_pct": success},
            )
            item = LearningInsightItem(
                category="pattern",
                title=f"{topic}: difficulty converting attempts to solutions",
                summary=f"Solved only {solved} of {total} attempted {topic} problems ({success:.0f}%).",
                evidence=f"{total} {topic} problem(s) recorded, {solved} solved.",
                impact="Gaps here slow down multi-topic problems that build on this area.",
                interpretation="Recurring struggle supported by multiple attempts, not a single failure.",
                action=f"Revisit the core {topic} concept with two guided problems before harder ones.",
                priority="high" if success < 34.0 else "medium",
                confidence="recurring" if total >= 3 else "early_signal",
                topics=[topic],
                evidence_refs=writer.refs(ref, suc_ref, acc_ref),
            )
            weaknesses.append(item)
            struggles.append(item)
        elif submissions >= 3 and acceptance < 50.0:
            ref = writer.add(
                _make_evidence_id("collective", "weakness", "attempts", key),
                f"collective.weakness.attempts.{key}",
                f"Repeated failed {topic} attempts",
                {"submissions": submissions, "acceptance_rate_pct": acceptance},
            )
            item = LearningInsightItem(
                category="pattern",
                title=f"{topic}: repeated failed submissions before success",
                summary=f"{submissions} {topic} submissions with only {acceptance:.0f}% accepted.",
                evidence="Computed from recorded submission verdicts.",
                impact="Signals the first attempted approach is frequently not yet correct.",
                interpretation="Recurring accuracy issue rather than a topic knowledge gap.",
                action="Before submitting, re-check boundary conditions and the algorithm's invariant.",
                priority="medium",
                confidence="recurring" if submissions >= 4 else "early_signal",
                topics=[topic],
                evidence_refs=writer.refs(ref, acc_ref),
            )
            weaknesses.append(item)
            struggles.append(item)

    if evidence.patterns.repeated_tle_problems:
        tle = evidence.patterns.repeated_tle_problems
        ref = writer.add(
            _make_evidence_id("collective", "weakness", "repeated_tle"),
            "collective.weakness.repeated_tle",
            "Problems with repeated Time Limit Exceeded",
            tle,
        )
        item = LearningInsightItem(
            category="pattern",
            title="Time-limit pressure on repeated attempts",
            summary=f"{len(tle)} problem(s) recorded repeated Time Limit Exceeded verdicts.",
            evidence="Problems: " + ", ".join(tle[:5]) + ".",
            impact="Indicates complexity is chosen after implementation rather than before it.",
            interpretation="Recurring efficiency issue supported by multiple TLE verdicts.",
            action="Estimate the required complexity before coding, then pick a matching pattern.",
            priority="high" if len(tle) >= 2 else "medium",
            confidence="recurring" if len(tle) >= 2 else "early_signal",
            examples=tle[:5],
            evidence_refs=writer.refs(ref),
        )
        weaknesses.append(item)
        struggles.append(item)

    if evidence.patterns.repeated_wa_problems:
        wa = evidence.patterns.repeated_wa_problems
        ref = writer.add(
            _make_evidence_id("collective", "weakness", "repeated_wa"),
            "collective.weakness.repeated_wa",
            "Problems with repeated Wrong Answer",
            wa,
        )
        item = LearningInsightItem(
            category="pattern",
            title="Boundary and edge-case handling",
            summary=f"{len(wa)} problem(s) recorded repeated Wrong Answer verdicts.",
            evidence="Problems: " + ", ".join(wa[:5]) + ".",
            impact="Edge cases (empty input, duplicates, extremes) are the most common WA source.",
            interpretation="Recurring correctness pattern across distinct problems.",
            action="Before submitting, walk through empty, single-element, duplicate and extreme inputs.",
            priority="high" if len(wa) >= 2 else "medium",
            confidence="recurring" if len(wa) >= 2 else "early_signal",
            examples=wa[:5],
            evidence_refs=writer.refs(ref),
        )
        weaknesses.append(item)
        struggles.append(item)

    recog = _optimization_recognition_weakness(records, writer)
    if recog is not None:
        weaknesses.append(recog)
        struggles.append(recog)

    if profile.avg_attempts_per_solved_problem >= 3.0 and profile.total_solved >= 3:
        ref = writer.ref(_make_evidence_id("analytics", "overview", "avg_attempts_per_solved_problem"))
        item = LearningInsightItem(
            category="pattern",
            title="High number of attempts per solved problem",
            summary=f"Average {profile.avg_attempts_per_solved_problem:.1f} attempts per solved problem.",
            evidence="Computed across all solved problems.",
            impact="Refining the approach in code costs more submissions than planning it first.",
            interpretation="Recurring first-attempt inaccuracy.",
            action="Spend an extra minute planning the algorithm and edge cases before the first submission.",
            priority="medium",
            confidence="recurring" if profile.avg_attempts_per_solved_problem >= 4 else "early_signal",
            evidence_refs=writer.refs(ref or ""),
        )
        weaknesses.append(item)
        struggles.append(item)

    weaknesses.sort(
        key=lambda i: ({"high": 0, "medium": 1, "low": 2}[i.priority], 0 if i.confidence == "recurring" else 1)
    )
    return weaknesses, struggles


def _optimization_recognition_weakness(
    records: Sequence[_SubmissionRecord],
    writer: _EvidenceWriter,
) -> Optional[LearningInsightItem]:
    """Detect problems whose FIRST attempt used nested loops but a later did not."""
    per_problem: dict[str, list[_SubmissionRecord]] = defaultdict(list)
    for rec in records:
        per_problem[rec.problem.slug].append(rec)

    examples: list[tuple[str, str, str]] = []
    for recs in per_problem.values():
        if len(recs) < 2:
            continue
        first = recs[0]
        if not (first.signals.has_code and first.signals.has_nested_loops):
            continue
        improved = next(
            (
                r
                for r in recs[1:]
                if r.signals.has_code and not r.signals.has_nested_loops and _is_accepted(r.submission)
            ),
            None,
        )
        if improved is not None:
            examples.append((first.problem.title, first.time_complexity, improved.time_complexity))

    if not examples:
        return None
    titles = [e[0] for e in examples]
    ref = writer.add(
        _make_evidence_id("collective", "weakness", "optimization_recognition"),
        "collective.weakness.optimization_recognition",
        "Optimization recognized after a first nested-loop attempt",
        {"count": len(examples), "examples": titles},
    )
    detail = ", ".join(f"{t} ({a} -> {b})" for t, a, b in examples[:3])
    return LearningInsightItem(
        category="pattern",
        title="Optimization is recognized after implementation",
        summary=(
            f"{len(examples)} problem(s) began with nested-loop code before a later attempt removed the "
            "nested traversal."
        ),
        evidence=detail + ".",
        impact="Avoidable O(n²) first attempts cost extra submissions before the real pattern is found.",
        interpretation=(
            "Suggests optimization opportunities are spotted during implementation rather than during "
            "algorithm selection."
        ),
        action=(
            "Before coding, ask whether each inner lookup can be replaced by hashing, sorting, or pointer movement."
        ),
        priority="high" if len(examples) >= 2 else "medium",
        confidence="recurring" if len(examples) >= 2 else "early_signal",
        examples=titles[:4],
        evidence_refs=writer.refs(ref),
    )

_MISTAKE_RULES: list[tuple[str, tuple[str, ...], str, str]] = [
    ("Boundary / off-by-one", ("off-by-one", "off by one", "boundary", "index out", "indexerror", "out of range"),
     "Boundary conditions are mishandled, producing wrong answers on edge inputs.",
     "Walk the first and last iteration by hand, and test the single-element case."),
    ("Correctness on edge cases", ("wrong answer",),
     "Submissions were rejected for incorrect output on some inputs.",
     "Before submitting, trace the empty, single-element, duplicate and extreme inputs."),
    ("Duplicate handling", ("duplicate",),
     "Duplicate values are not handled as a distinct case.",
     "Decide explicitly what happens for repeated values before writing the loop."),
    ("Empty / null input", ("empty", "null", "none type", "nonetype"),
     "Empty or missing input is not handled.",
     "Add an explicit early return for empty input."),
    ("Overflow / large values", ("overflow", "integer limit", "large values"),
     "Numeric extremes cause incorrect results.",
     "Check the numeric bounds implied by the constraints before choosing a type."),
    ("Recursion depth", ("recursion", "maximum recursion", "stack depth", "recursionerror"),
     "Deep recursion risks stack overflow.",
     "Consider an iterative traversal or an explicit stack."),
    ("Base case / termination", ("base case", "termination"),
     "A terminating base case is missing or incorrect.",
     "State the base case first, then the recursive/loop step."),
    ("Complexity choice", ("time limit", "o(n²)", "o(n^2)", "nested loop", "too slow", "inefficient"),
     "The chosen complexity is too high for the input bounds.",
     "Estimate the allowed complexity from the constraints before choosing an approach."),
    ("Wrong data structure", ("wrong data structure", "suboptimal data structure", "should use a hash", "should use a set"),
     "A structure with the wrong access cost was chosen.",
     "List the operations needed and pick the structure with the right cost for each."),
]


def _detect_recurring_mistakes(
    records: Sequence[_SubmissionRecord],
    writer: _EvidenceWriter,
) -> list[LearningInsightItem]:
    counter: Counter[str] = Counter()
    examples: dict[str, list[str]] = defaultdict(list)

    for rec in records:
        if _is_accepted(rec.submission):
            continue
        text_parts: list[str] = []
        if rec.analysis:
            text_parts.extend(
                [
                    rec.analysis.potential_issues or "",
                    rec.analysis.weaknesses or "",
                    " ".join(rec.analysis.likely_explanations or []),
                ]
            )
        text = " ".join(text_parts).lower()
        for label, tokens, _impact, _prevent in _MISTAKE_RULES:
            if any(tok in text for tok in tokens):
                counter[label] += 1
                if rec.problem.title not in examples[label]:
                    examples[label].append(rec.problem.title)

    for rec in records:
        if rec.submission.status == SubmissionStatus.TIME_LIMIT_EXCEEDED:
            counter["Complexity choice"] += 1
            if rec.problem.title not in examples["Complexity choice"]:
                examples["Complexity choice"].append(rec.problem.title)
        elif rec.submission.status == SubmissionStatus.WRONG_ANSWER:
            counter["Correctness on edge cases"] += 1
            if rec.problem.title not in examples["Correctness on edge cases"]:
                examples["Correctness on edge cases"].append(rec.problem.title)

    items: list[LearningInsightItem] = []
    for label, _tokens, impact, prevention in _MISTAKE_RULES:
        count = counter.get(label, 0)
        if count < 2:
            # A single observation is not "recurring" -- do not label it as such.
            continue
        key = label.lower().replace(" ", "_").replace("/", "_")
        ref = writer.add(
            _make_evidence_id("collective", "mistake", key),
            f"collective.mistake.{key}",
            f"Recurring mistake: {label}",
            {"count": count, "examples": examples[label]},
        )
        items.append(
            LearningInsightItem(
                category="pattern",
                title=label,
                summary=f"Observed across {count} submission(s).",
                evidence="Representative problems: " + ", ".join(examples[label][:4]) + ".",
                impact=impact,
                interpretation="Recurring mistake supported by multiple independent submissions.",
                action=prevention,
                priority="high" if count >= 3 else "medium",
                confidence="recurring",
                examples=examples[label][:4],
                evidence_refs=writer.refs(ref),
            )
        )
    items.sort(key=lambda i: ({"high": 0, "medium": 1, "low": 2}[i.priority], -len(i.examples)))
    return items


def _detect_optimization_trends(
    records: Sequence[_SubmissionRecord],
    writer: _EvidenceWriter,
) -> list[LearningInsightItem]:
    per_problem: dict[str, list[_SubmissionRecord]] = defaultdict(list)
    for rec in records:
        per_problem[rec.problem.slug].append(rec)

    improvements: list[tuple[str, str, str]] = []
    regressions: list[tuple[str, str, str]] = []
    flat: list[tuple[str, str]] = []

    for recs in per_problem.values():
        if len(recs) < 2:
            continue
        first, last = recs[0], recs[-1]
        a = complexity_rank(first.time_complexity)
        b = complexity_rank(last.time_complexity)
        if a is None or b is None:
            continue
        if b < a:
            improvements.append((first.problem.title, first.time_complexity, last.time_complexity))
        elif b > a:
            regressions.append((first.problem.title, first.time_complexity, last.time_complexity))
        else:
            flat.append((first.problem.title, first.time_complexity))

    items: list[LearningInsightItem] = []
    if improvements:
        ref = writer.add(
            _make_evidence_id("collective", "trend", "optimization", "improved"),
            "collective.trend.optimization.improved",
            "Attempts that reduced complexity",
            improvements,
        )
        detail = ", ".join(f"{t} ({a} -> {b})" for t, a, b in improvements[:3])
        items.append(
            LearningInsightItem(
                category="fact",
                title="Solutions are being optimized across attempts",
                summary=f"{len(improvements)} problem(s) ended at a cheaper complexity than the first attempt.",
                evidence=detail + ".",
                impact="Shows the optimization reflex works once a bottleneck is noticed.",
                interpretation="Positive before/after trend computed from recorded complexity labels.",
                action="Aim for the cheaper approach on the first attempt instead of the last.",
                priority="medium",
                confidence="recurring" if len(improvements) >= 2 else "early_signal",
                examples=[t for t, _, _ in improvements[:4]],
                evidence_refs=writer.refs(ref),
            )
        )
    if regressions:
        ref = writer.add(
            _make_evidence_id("collective", "trend", "optimization", "regressed"),
            "collective.trend.optimization.regressed",
            "Attempts that increased complexity",
            regressions,
        )
        detail = ", ".join(f"{t} ({a} -> {b})" for t, a, b in regressions[:3])
        items.append(
            LearningInsightItem(
                category="fact",
                title="Some later attempts became more expensive",
                summary=f"{len(regressions)} problem(s) ended at a higher complexity than the first attempt.",
                evidence=detail + ".",
                impact="Later rewrites can trade away efficiency for correctness -- worth checking deliberately.",
                interpretation="Regression detected from recorded complexity labels.",
                action="When rewriting for correctness, re-check that the complexity did not regress.",
                priority="medium",
                confidence="recurring" if len(regressions) >= 2 else "early_signal",
                examples=[t for t, _, _ in regressions[:4]],
                evidence_refs=writer.refs(ref),
            )
        )
    if flat and not improvements:
        ref = writer.add(
            _make_evidence_id("collective", "trend", "optimization", "flat"),
            "collective.trend.optimization.flat",
            "No complexity change across attempts",
            flat,
        )
        detail = ", ".join(f"{t} stayed at {c}" for t, c in flat[:3])
        items.append(
            LearningInsightItem(
                category="pattern",
                title="No complexity improvement across repeated attempts",
                summary=f"{len(flat)} problem(s) kept the same complexity across attempts.",
                evidence=detail + ".",
                impact="Repeated submissions did not change the asymptotic cost.",
                interpretation="Optimization opportunities are not being acted on when they appear.",
                action="After a re-attempt, ask what the complexity changed from and to.",
                priority="medium",
                confidence="recurring" if len(flat) >= 2 else "early_signal",
                examples=[t for t, _ in flat[:4]],
                evidence_refs=writer.refs(ref),
            )
        )
    return items


def _detect_progress(
    evidence: InsightEvidence,
    records: Sequence[_SubmissionRecord],
    writer: _EvidenceWriter,
) -> list[LearningProgressTrend]:
    if len(records) < _PROGRESS_MIN_SUBMISSIONS:
        return []
    mid = len(records) // 2
    earlier, recent = records[:mid], records[mid:]

    def _rate(recs: Sequence[_SubmissionRecord]) -> float:
        return sum(1 for r in recs if _is_accepted(r.submission)) / len(recs) * 100.0 if recs else 0.0

    def _avg_rank(recs: Sequence[_SubmissionRecord]) -> float | None:
        ranks = [complexity_rank(r.time_complexity) for r in recs if _is_accepted(r.submission)]
        valid = [r for r in ranks if r is not None]
        return sum(valid) / len(valid) if valid else None

    trends: list[LearningProgressTrend] = []
    e_rate, r_rate = _rate(earlier), _rate(recent)
    ref = writer.add(
        _make_evidence_id("collective", "progress", "acceptance_rate"),
        "collective.progress.acceptance_rate",
        "Acceptance rate: earlier vs recent submissions",
        {"earlier_pct": round(e_rate, 1), "recent_pct": round(r_rate, 1)},
    )
    trends.append(
        LearningProgressTrend(
            metric="Acceptance rate",
            earlier=f"{e_rate:.0f}%",
            recent=f"{r_rate:.0f}%",
            delta=f"{r_rate - e_rate:+.0f} pts",
            summary=f"Acceptance moved from {e_rate:.0f}% (earlier half) to {r_rate:.0f}% (recent half).",
            evidence_refs=writer.refs(ref),
        )
    )

    e_rank, r_rank = _avg_rank(earlier), _avg_rank(recent)
    if e_rank is not None and r_rank is not None:
        ref = writer.add(
            _make_evidence_id("collective", "progress", "complexity"),
            "collective.progress.complexity",
            "Average complexity rank: earlier vs recent accepted submissions",
            {"earlier_rank": round(e_rank, 2), "recent_rank": round(r_rank, 2)},
        )
        direction = "cheaper" if r_rank < e_rank else ("more expensive" if r_rank > e_rank else "unchanged")
        trends.append(
            LearningProgressTrend(
                metric="Solution complexity",
                earlier=f"rank {e_rank:.2f}",
                recent=f"rank {r_rank:.2f}",
                delta=f"{r_rank - e_rank:+.2f}",
                summary=f"Accepted solutions are {direction} in the recent half (lower rank = cheaper).",
                evidence_refs=writer.refs(ref),
            )
        )

    e_diff = _solved_difficulty(earlier)
    r_diff = _solved_difficulty(recent)
    if e_diff or r_diff:
        ref = writer.add(
            _make_evidence_id("collective", "progress", "difficulty"),
            "collective.progress.difficulty",
            "Difficulty mix: earlier vs recent solved problems",
            {"earlier": e_diff, "recent": r_diff},
        )
        trends.append(
            LearningProgressTrend(
                metric="Difficulty mix",
                earlier=", ".join(f"{k}:{v}" for k, v in e_diff.items()) or "none",
                recent=", ".join(f"{k}:{v}" for k, v in r_diff.items()) or "none",
                summary="Distribution of solved-problem difficulty in each period.",
                evidence_refs=writer.refs(ref),
            )
        )
    return trends


def _solved_difficulty(recs: Sequence[_SubmissionRecord]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for rec in recs:
        if _is_accepted(rec.submission):
            diff = rec.problem.difficulty
            counts[str(diff.value if hasattr(diff, "value") else diff)] += 1
    return dict(counts)


def _rank_focus_areas(
    unpracticed: Sequence[LearningInsightItem],
    struggles: Sequence[LearningInsightItem],
    mistakes: Sequence[LearningInsightItem],
) -> list[LearningInsightItem]:
    priority_order = {"high": 0, "medium": 1, "low": 2}
    focus: list[LearningInsightItem] = [item.model_copy(update={"category": "action"}) for item in struggles]
    for item in mistakes:
        if len(focus) >= 4:
            break
        focus.append(item.model_copy(update={"category": "action"}))
    for item in unpracticed:
        if len(focus) >= 5:
            break
        focus.append(item.model_copy(update={"category": "action"}))
    focus.sort(key=lambda i: priority_order.get(i.priority, 1))
    return focus


def _build_actions(
    focus_areas: Sequence[LearningInsightItem],
    mistakes: Sequence[LearningInsightItem],
    trends: Sequence[LearningInsightItem],
) -> list[str]:
    actions: list[str] = []
    for item in list(focus_areas) + list(mistakes) + list(trends):
        if item.action and item.action not in actions:
            actions.append(item.action)
    return actions


def _build_summary(
    profile: CollectiveLearningProfile,
    strengths: Sequence[LearningInsightItem],
    weaknesses: Sequence[LearningInsightItem],
    trends: Sequence[LearningInsightItem],
) -> str:
    if profile.total_problems == 0:
        return "No problems have been recorded yet. Import or sync submissions to build a learning profile."
    parts = [
        f"Across {profile.total_problems} recorded problem(s), {profile.total_solved} are solved "
        f"({profile.acceptance_rate_pct:.0f}% overall acceptance)."
    ]
    if strengths:
        parts.append("Strongest demonstrated areas: " + ", ".join(s.title for s in strengths[:2]) + ".")
    if weaknesses:
        parts.append("Recurring improvement areas: " + ", ".join(w.title for w in weaknesses[:2]) + ".")
    if trends:
        parts.append(trends[0].summary)
    if profile.total_problems < _EARLY_STAGE_PROBLEMS:
        parts.append("This is an early-stage profile; conclusions are deliberately cautious.")
    return " ".join(parts)
