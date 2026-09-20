"""Pure-data evidence builder for the grounded insight pipeline.

Calls existing deterministic analytics services and gathers cached AI
submission analyses to produce a typed ``InsightEvidence`` bundle.

This module contains **zero** LLM calls. It does not generate prose
conclusions, does not invent statistics, and does not trigger new AI
analysis.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from codememory.ai.evidence_models import (
    EvidenceComparison,
    EvidenceItem,
    EvidenceMetrics,
    EvidencePatterns,
    InsightEvidence,
    ProblemSnapshot,
    SubmissionSnapshot,
    _make_evidence_id,
)
from codememory.analytics.analytics_service import AnalyticsService
from codememory.analytics.pattern_analyzer import PatternAnalyzer
from codememory.domain.exceptions import ProblemNotFoundError

if TYPE_CHECKING:
    from codememory.ai.analyzer import AICodeAnalyzer
    from codememory.storage.composite_repository import CompositeStorage

# Minimum number of problems in a topic before its statistics are
# considered reliable.  Topics with fewer problems get an explicit
# limitation note attached to the evidence.
_MIN_SAMPLE_SIZE = 3


class EvidenceBuilder:
    """Assembles ``InsightEvidence`` from existing deterministic services.

    This is a pure-data orchestration layer. It never invokes an LLM and
    never triggers new AI submission analysis.
    """

    def __init__(
        self,
        analytics_service: AnalyticsService,
        pattern_analyzer: PatternAnalyzer,
        ai_analyzer: Optional["AICodeAnalyzer"] = None,
        storage: Optional["CompositeStorage"] = None,
    ):
        self.analytics = analytics_service
        self.pattern_analyzer = pattern_analyzer
        self.ai_analyzer = ai_analyzer
        self.storage = storage

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_full_profile_evidence(self) -> InsightEvidence:
        """Build evidence covering the user's full practice profile."""
        evidence = InsightEvidence(scope="full_profile", generated_at=datetime.now(timezone.utc))

        # 1. Overview metrics
        overview = self.analytics.get_overview()
        overview_dict = overview.model_dump()
        evidence.metrics.overview = overview_dict
        self._add_overview_items(evidence, overview_dict)

        # 2. Topic statistics
        topic_stats = self.analytics.get_topic_statistics()
        evidence.metrics.topic_stats = [ts.model_dump() for ts in topic_stats]
        overall_acc_rate = overview.overall_acceptance_rate_pct
        self._add_topic_items(evidence, topic_stats, overall_acc_rate)

        # 3. Difficulty statistics
        diff_stats = self.analytics.get_difficulty_statistics()
        evidence.metrics.difficulty_stats = [ds.model_dump() for ds in diff_stats]
        self._add_difficulty_items(evidence, diff_stats)

        # 4. Attempt statistics
        att_stats = self.analytics.get_attempt_statistics()
        evidence.metrics.attempt_stats = att_stats.model_dump()

        # 5. Pattern analysis
        patterns = self.pattern_analyzer.analyze()
        self._populate_patterns(evidence, patterns)

        # 6. Struggle problems
        struggles = self.analytics.get_struggle_problems(limit=10)
        for sp in struggles:
            diff_str = sp.difficulty
            evidence.supporting_problems.append(
                ProblemSnapshot(
                    problem_id=sp.problem_id,
                    title=sp.title,
                    slug=sp.slug,
                    difficulty=diff_str,
                    topics=sp.topics,
                    total_attempts=sp.total_attempts,
                    status=sp.status,
                )
            )

        # 7. Cached submission analyses (optional, never triggers new analysis)
        self._add_cached_submission_snapshots(evidence, struggles)

        # 8. Limitations
        self._compute_limitations(evidence, topic_stats)

        return evidence

    def build_topic_evidence(self, topic: str) -> InsightEvidence:
        """Build evidence focused on a single DSA topic."""
        evidence = InsightEvidence(
            scope=f"topic:{topic}",
            generated_at=datetime.now(timezone.utc),
        )

        # Overview for baseline comparison
        overview = self.analytics.get_overview()
        overview_dict = overview.model_dump()
        evidence.metrics.overview = overview_dict
        self._add_overview_items(evidence, overview_dict)

        # Filter topic stats to the requested topic
        all_topic_stats = self.analytics.get_topic_statistics()
        matching = [ts for ts in all_topic_stats if ts.topic.lower() == topic.lower()]
        evidence.metrics.topic_stats = [ts.model_dump() for ts in matching]

        overall_acc_rate = overview.overall_acceptance_rate_pct
        self._add_topic_items(evidence, matching, overall_acc_rate)

        # Patterns (full, but consumer can focus on the relevant topic)
        patterns = self.pattern_analyzer.analyze()
        self._populate_patterns(evidence, patterns)

        # Struggle problems filtered by topic
        struggles = self.analytics.get_struggle_problems(limit=20)
        topic_lower = topic.lower()
        for sp in struggles:
            if any(t.lower() == topic_lower for t in sp.topics):
                evidence.supporting_problems.append(
                    ProblemSnapshot(
                        problem_id=sp.problem_id,
                        title=sp.title,
                        slug=sp.slug,
                        difficulty=sp.difficulty,
                        topics=sp.topics,
                        total_attempts=sp.total_attempts,
                        status=sp.status,
                    )
                )

        self._add_cached_submission_snapshots(evidence, struggles)
        self._compute_limitations(evidence, matching)

        return evidence

    def build_problem_evidence(self, problem_identifier: str) -> InsightEvidence:
        """Build evidence focused on a single problem.

        Uses the repository's canonical problem identifier (slug or ID).
        """
        if not self.storage:
            return InsightEvidence(
                scope=f"problem:{problem_identifier}",
                generated_at=datetime.now(timezone.utc),
                limitations=["Storage not available for problem-level evidence."],
            )

        prob = self.storage.get_by_slug(problem_identifier) or self.storage.get_by_id(problem_identifier)
        if not prob:
            raise ProblemNotFoundError(problem_identifier)

        evidence = InsightEvidence(
            scope=f"problem:{prob.slug}",
            generated_at=datetime.now(timezone.utc),
        )

        # Problem snapshot
        diff_str = prob.difficulty.value if hasattr(prob.difficulty, "value") else str(prob.difficulty)
        status = "Solved" if prob.latest_accepted_submission else "Unsolved"
        evidence.supporting_problems.append(
            ProblemSnapshot(
                problem_id=prob.id,
                title=prob.title,
                slug=prob.slug,
                difficulty=diff_str,
                topics=prob.topics,
                total_attempts=len(prob.attempts),
                status=status,
            )
        )

        # Evidence items for this problem
        evidence.items.append(EvidenceItem(
            evidence_id=_make_evidence_id("problem", prob.slug, "total_attempts"),
            source=f"problem.{prob.slug}",
            source_type="deterministic",
            label=f"{prob.title} total attempts",
            value=len(prob.attempts),
        ))
        evidence.items.append(EvidenceItem(
            evidence_id=_make_evidence_id("problem", prob.slug, "status"),
            source=f"problem.{prob.slug}",
            source_type="deterministic",
            label=f"{prob.title} status",
            value=status,
        ))

        # Collect submission IDs and add cached analyses
        all_sub_ids: list[str] = []
        for att in prob.attempts:
            for sub in att.submissions:
                all_sub_ids.append(sub.id)

        if self.ai_analyzer and all_sub_ids:
            cached = self.ai_analyzer.get_cached_analyses(submission_ids=all_sub_ids)
            for sub_id, analysis in cached.items():
                evidence.supporting_submissions.append(
                    SubmissionSnapshot(
                        submission_id=sub_id,
                        problem_title=prob.title,
                        approach=analysis.approach,
                        time_complexity=analysis.time_complexity,
                        space_complexity=analysis.space_complexity,
                        correctness_summary=analysis.correctness_summary,
                        potential_issues=analysis.potential_issues,
                    )
                )
                evidence.items.append(EvidenceItem(
                    evidence_id=_make_evidence_id("ai_analysis", "submission", sub_id, "approach"),
                    source=f"ai_analysis.submission.{sub_id}",
                    source_type="ai_analysis",
                    label=f"Submission {sub_id[:8]}… approach",
                    value=analysis.approach,
                ))

        return evidence

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _add_overview_items(self, evidence: InsightEvidence, overview_dict: dict) -> None:
        """Create EvidenceItems for overview metrics."""
        field_meta = {
            "total_problems": ("Total problems", None),
            "total_attempts": ("Total attempts", None),
            "total_submissions": ("Total submissions", None),
            "accepted_problems": ("Solved problems", None),
            "unsolved_problems": ("Unsolved problems", None),
            "overall_acceptance_rate_pct": ("Overall acceptance rate", "%"),
            "avg_attempts_per_solved_problem": ("Avg attempts per solved problem", None),
            "first_attempt_acceptance_rate_pct": ("First-attempt acceptance rate", "%"),
            "repeated_problem_rate_pct": ("Repeated problem rate", "%"),
        }
        for field, (label, unit) in field_meta.items():
            value = overview_dict.get(field)
            if value is not None:
                evidence.items.append(EvidenceItem(
                    evidence_id=_make_evidence_id("analytics", "overview", field),
                    source="analytics.overview",
                    source_type="deterministic",
                    label=label,
                    value=value,
                    unit=unit,
                ))

    def _add_topic_items(self, evidence: InsightEvidence, topic_stats: list, overall_acc_rate: float) -> None:
        """Create EvidenceItems and EvidenceComparisons for topic statistics."""
        overall_eid = _make_evidence_id("analytics", "overview", "overall_acceptance_rate_pct")
        for ts in topic_stats:
            topic_key = ts.topic.lower().replace(" ", "_").replace("-", "_")
            source = f"analytics.topic_stats.{topic_key}"

            # Acceptance rate item
            acc_eid = _make_evidence_id("analytics", "topic_stats", topic_key, "acceptance_rate")
            evidence.items.append(EvidenceItem(
                evidence_id=acc_eid,
                source=source,
                source_type="deterministic",
                label=f"{ts.topic} acceptance rate",
                value=ts.acceptance_rate_pct,
                unit="%",
                sample_size=ts.total_submissions,
            ))

            # Problem count item
            evidence.items.append(EvidenceItem(
                evidence_id=_make_evidence_id("analytics", "topic_stats", topic_key, "problem_count"),
                source=source,
                source_type="deterministic",
                label=f"{ts.topic} problem count",
                value=ts.total_problems,
            ))

            # Success rate item
            evidence.items.append(EvidenceItem(
                evidence_id=_make_evidence_id("analytics", "topic_stats", topic_key, "success_rate"),
                source=source,
                source_type="deterministic",
                label=f"{ts.topic} success rate",
                value=ts.success_rate_pct,
                unit="%",
                sample_size=ts.total_problems,
            ))

            # Comparison against overall
            delta = round(ts.acceptance_rate_pct - overall_acc_rate, 2)
            evidence.comparisons.append(EvidenceComparison(
                evidence_id=_make_evidence_id("comparison", topic_key + "_vs_overall", "acceptance_rate"),
                label=f"{ts.topic} vs overall acceptance rate",
                topic_evidence_id=acc_eid,
                overall_evidence_id=overall_eid,
                topic_rate=ts.acceptance_rate_pct,
                overall_rate=overall_acc_rate,
                delta=delta,
            ))

    def _add_difficulty_items(self, evidence: InsightEvidence, diff_stats: list) -> None:
        """Create EvidenceItems for difficulty statistics."""
        for ds in diff_stats:
            diff_key = ds.difficulty.lower().replace(" ", "_")
            source = f"analytics.difficulty_stats.{diff_key}"
            evidence.items.append(EvidenceItem(
                evidence_id=_make_evidence_id("analytics", "difficulty_stats", diff_key, "acceptance_rate"),
                source=source,
                source_type="deterministic",
                label=f"{ds.difficulty} acceptance rate",
                value=ds.acceptance_rate_pct,
                unit="%",
                sample_size=ds.total_submissions,
            ))
            evidence.items.append(EvidenceItem(
                evidence_id=_make_evidence_id("analytics", "difficulty_stats", diff_key, "problem_count"),
                source=source,
                source_type="deterministic",
                label=f"{ds.difficulty} problem count",
                value=ds.total_problems,
            ))

    def _populate_patterns(self, evidence: InsightEvidence, patterns) -> None:
        """Populate evidence patterns and create pattern-level EvidenceItems."""
        evidence.patterns.weak_topics = list(patterns.weak_topics)
        evidence.patterns.high_failure_topics = list(patterns.high_failure_topics)
        evidence.patterns.repeated_tle_problems = list(patterns.repeated_tle_problems)
        evidence.patterns.repeated_wa_problems = list(patterns.repeated_wa_problems)
        evidence.patterns.brute_force_before_optimized_problems = list(patterns.brute_force_before_optimized_problems)
        evidence.patterns.high_attempt_problems = list(patterns.high_attempt_problems)
        evidence.patterns.improvement_patterns = list(patterns.improvement_patterns)
        evidence.patterns.unpracticed_topics = list(patterns.unpracticed_topics)

        # Create traceable EvidenceItems for key patterns
        for wt in patterns.weak_topics:
            topic = wt.get("topic", "unknown")
            topic_key = topic.lower().replace(" ", "_").replace("-", "_")
            evidence.items.append(EvidenceItem(
                evidence_id=_make_evidence_id("pattern_analyzer", "weak_topics", topic_key),
                source="pattern_analyzer.weak_topics",
                source_type="deterministic",
                label=f"Weak topic: {topic}",
                value=wt,
                sample_size=wt.get("total_problems"),
            ))

        for hf in patterns.high_failure_topics:
            topic = hf.get("topic", "unknown")
            topic_key = topic.lower().replace(" ", "_").replace("-", "_")
            evidence.items.append(EvidenceItem(
                evidence_id=_make_evidence_id("pattern_analyzer", "high_failure_topics", topic_key),
                source="pattern_analyzer.high_failure_topics",
                source_type="deterministic",
                label=f"High failure topic: {topic}",
                value=hf,
                sample_size=hf.get("total_submissions"),
            ))

        for imp in patterns.improvement_patterns:
            metric = imp.get("metric", "unknown")
            evidence.items.append(EvidenceItem(
                evidence_id=_make_evidence_id("pattern_analyzer", "improvement_patterns", metric),
                source="pattern_analyzer.improvement_patterns",
                source_type="deterministic",
                label=f"Improvement: {metric}",
                value=imp,
            ))

        for ut in patterns.unpracticed_topics:
            topic = ut.get("topic", "unknown")
            topic_key = topic.lower().replace(" ", "_").replace("-", "_")
            evidence.items.append(EvidenceItem(
                evidence_id=_make_evidence_id("pattern_analyzer", "unpracticed_topics", topic_key),
                source="pattern_analyzer.unpracticed_topics",
                source_type="deterministic",
                label=f"Unpracticed topic: {topic}",
                value=ut,
            ))

    def _add_cached_submission_snapshots(self, evidence: InsightEvidence, struggles) -> None:
        """Add cached AI analyses for struggle problems as supporting submissions.

        Uses ``AICodeAnalyzer.get_cached_analyses()`` — never triggers new
        analysis.
        """
        if not self.ai_analyzer:
            return

        # Collect all submission IDs from struggle problems via storage
        if not self.storage:
            return

        sub_ids: list[str] = []
        for sp in struggles:
            prob = self.storage.get_by_id(sp.problem_id)
            if prob:
                for att in prob.attempts:
                    for sub in att.submissions:
                        sub_ids.append(sub.id)

        if not sub_ids:
            return

        cached = self.ai_analyzer.get_cached_analyses(submission_ids=sub_ids)
        for sub_id, analysis in cached.items():
            # Find the problem title for this submission
            prob_title = "Unknown"
            for sp in struggles:
                prob = self.storage.get_by_id(sp.problem_id)
                if prob:
                    for att in prob.attempts:
                        if any(s.id == sub_id for s in att.submissions):
                            prob_title = sp.title
                            break

            evidence.supporting_submissions.append(
                SubmissionSnapshot(
                    submission_id=sub_id,
                    problem_title=prob_title,
                    approach=analysis.approach,
                    time_complexity=analysis.time_complexity,
                    space_complexity=analysis.space_complexity,
                    correctness_summary=analysis.correctness_summary,
                    potential_issues=analysis.potential_issues,
                )
            )
            evidence.items.append(EvidenceItem(
                evidence_id=_make_evidence_id("ai_analysis", "submission", sub_id, "approach"),
                source=f"ai_analysis.submission.{sub_id}",
                source_type="ai_analysis",
                label=f"Submission {sub_id[:8]}… approach",
                value=analysis.approach,
            ))

    def _compute_limitations(self, evidence: InsightEvidence, topic_stats: list) -> None:
        """Add limitations for genuinely small sample sizes."""
        for ts in topic_stats:
            total = ts.total_problems if hasattr(ts, "total_problems") else ts.get("total_problems", 0)
            topic = ts.topic if hasattr(ts, "topic") else ts.get("topic", "?")
            if total < _MIN_SAMPLE_SIZE:
                evidence.limitations.append(
                    f"Only {total} problem(s) in {topic} — statistics may not be representative."
                )

        overview = evidence.metrics.overview
        total_problems = overview.get("total_problems", 0)
        if 0 < total_problems < 5:
            evidence.limitations.append(
                f"Only {total_problems} total problem(s) — overall statistics are preliminary."
            )
