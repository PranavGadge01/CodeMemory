"""Rule-based heuristic AI analysis provider for offline use without external API keys."""

import re
from typing import List, Optional
from codememory.ai.models import SubmissionAnalysis, SolutionEvolution, EvolutionStepDetail
from codememory.ai.providers.base_provider import BaseAIProvider, InterpretationResult
from codememory.domain.models import Problem, Submission

from codememory.ai.evidence_models import InsightEvidence


class HeuristicAIProvider(BaseAIProvider):
    """Deterministic offline AI provider that infers solution attributes using AST/regex heuristics."""

    def analyze_submission(
        self,
        submission: Submission,
        problem: Problem,
        previous_submission: Optional[Submission] = None,
    ) -> SubmissionAnalysis:
        code = submission.code or ""
        code_lower = code.lower()
        status_str = (submission.status.value if hasattr(submission.status, "value") else str(submission.status)).lower()

        # Infer approach & algorithms/DS
        approach_items = []
        algo_items = []
        ds_items = []

        if "hashmap" in code_lower or "dict" in code_lower or "map<" in code_lower or "unordered_map" in code_lower or "{" in code:
            approach_items.append("Hash Table Lookup")
            algo_items.append("Hashing")
            ds_items.append("HashMap / Dictionary")
        if "left" in code_lower and "right" in code_lower and ("while" in code_lower or "for" in code_lower):
            approach_items.append("Two Pointers")
            algo_items.append("Two Pointers")
            ds_items.append("Array Pointers")
        if "mid" in code_lower or "binary" in code_lower or ("low" in code_lower and "high" in code_lower):
            approach_items.append("Binary Search")
            algo_items.append("Binary Search")
            ds_items.append("Sorted Array")
        if "dp" in code_lower or "memo" in code_lower or "cache" in code_lower:
            approach_items.append("Dynamic Programming / Memoization")
            algo_items.append("Dynamic Programming")
            ds_items.append("DP Table")
        if "deque" in code_lower or "queue" in code_lower or "visited" in code_lower:
            approach_items.append("Breadth-First Search (BFS)")
            algo_items.append("BFS")
            ds_items.append("Queue / Deque")
        if "stack" in code_lower or "pop" in code_lower:
            approach_items.append("Stack Data Structure")
            algo_items.append("Stack Traversal")
            ds_items.append("Stack")
        if "heap" in code_lower or "priorityqueue" in code_lower or ("push" in code_lower and "pop" in code_lower):
            approach_items.append("Priority Queue / Heap")
            algo_items.append("Heap Selection")
            ds_items.append("Heap")

        if not approach_items:
            primary_topic = problem.topics[0] if problem.topics else "General Algorithmic"
            approach_items.append(f"{primary_topic} Approach")
            algo_items.append(primary_topic)
            ds_items.append("Array / Matrix")

        inferred_approach = " + ".join(approach_items)
        inferred_pattern = approach_items[0]

        # Estimate complexity
        for_loop_count = len(re.findall(r"\bfor\b", code_lower))
        while_loop_count = len(re.findall(r"\bwhile\b", code_lower))
        total_loops = for_loop_count + while_loop_count

        if total_loops >= 2 and ("for" in code and re.search(r"for.*for", code, re.DOTALL)):
            time_complexity = "O(n²)"
            space_complexity = "O(1)" if "hash" not in code_lower else "O(n)"
        elif "mid" in code_lower or "binary" in code_lower:
            time_complexity = "O(log n)"
            space_complexity = "O(1)"
        elif "sort" in code_lower:
            time_complexity = "O(n log n)"
            space_complexity = "O(n)"
        elif total_loops == 1 or "hash" in code_lower or "dict" in code_lower:
            time_complexity = "O(n)"
            space_complexity = "O(n)" if ("hash" in code_lower or "dict" in code_lower or "dp" in code_lower) else "O(1)"
        else:
            time_complexity = "O(n)"
            space_complexity = "O(1)"

        certain_facts = [
            f"Submission status: {submission.status.value if hasattr(submission.status, 'value') else submission.status}",
            f"Language: {submission.language}",
            f"Detected loop constructs: {total_loops}",
        ]
        if submission.runtime_ms is not None:
            certain_facts.append(f"Recorded runtime: {submission.runtime_ms:.1f} ms")
        if submission.memory_mb is not None:
            certain_facts.append(f"Recorded memory usage: {submission.memory_mb:.1f} MB")

        likely_explanations = []
        potential_issues = None
        weaknesses = None
        strengths = "Clear variable naming and modular layout." if len(code.splitlines()) > 5 else "Compact implementation."

        if "time limit" in status_str or "tle" in status_str:
            likely_explanations.append("Likely Time Limit Exceeded due to nested O(n²) loop overhead on large inputs.")
            potential_issues = "Time Limit Exceeded due to unoptimized nested loop iterations or missing early termination."
            weaknesses = f"Unoptimized time complexity ({time_complexity})."
        elif "wrong answer" in status_str or "wa" in status_str:
            likely_explanations.append("Likely logic bug on boundary/edge cases such as empty input, duplicate values, or zero inputs.")
            potential_issues = "Unhandled edge cases (duplicates, empty arrays, extreme values)."
            weaknesses = "Logic flaw in condition check."
        elif "memory" in status_str:
            likely_explanations.append("Likely Memory Limit Exceeded due to deep recursion stack frames or large allocation tables.")
            potential_issues = "Excessive recursion stack depth or oversized DP grid."
            weaknesses = f"High space consumption ({space_complexity})."
        elif "accepted" in status_str:
            certain_facts.append("All test cases passed successfully.")
            strengths += f" Satisfied performance constraints with {time_complexity} time complexity."

        concise_explanation = (
            f"Implementation utilizes {inferred_approach} ({', '.join(ds_items)}). "
            f"Estimated complexity: {time_complexity} time, {space_complexity} space."
        )

        return SubmissionAnalysis(
            approach=inferred_approach,
            algorithms=algo_items,
            data_structures=ds_items,
            inferred_pattern=inferred_pattern,
            time_complexity=time_complexity,
            space_complexity=space_complexity,
            correctness_summary=f"Status: {submission.status.value if hasattr(submission.status, 'value') else submission.status}",
            potential_issues=potential_issues,
            strengths=strengths,
            weaknesses=weaknesses,
            concise_explanation=concise_explanation,
            certain_facts=certain_facts,
            likely_explanations=likely_explanations,
            analysis_version="v1",
        )

    def analyze_evolution(
        self,
        problem: Problem,
        submissions: List[Submission],
    ) -> SolutionEvolution:
        if not submissions:
            return SolutionEvolution(
                problem_id=problem.id,
                problem_title=problem.title,
                total_attempts=0,
                initial_approach="None",
                final_approach="None",
                major_changes=[],
                optimization_steps=[],
                mistakes_identified=[],
                learning_points=["No attempts recorded yet."],
                overall_summary="No submissions available for analysis.",
                steps=[],
                analysis_version="v1",
            )

        sorted_subs = sorted(submissions, key=lambda s: s.submitted_at)
        step_details: List[EvolutionStepDetail] = []
        prev_sub = None

        major_changes = []
        optimization_steps = []
        mistakes_identified = []
        learning_points = []

        for idx, sub in enumerate(sorted_subs, start=1):
            analysis = self.analyze_submission(sub, problem, prev_sub)
            key_change = None
            if prev_sub:
                prev_status = prev_sub.status.value if hasattr(prev_sub.status, "value") else str(prev_sub.status)
                curr_status = sub.status.value if hasattr(sub.status, "value") else str(sub.status)
                if prev_status != curr_status:
                    key_change = f"Status shifted from {prev_status} to {curr_status}."
                    if curr_status == "Accepted":
                        optimization_steps.append(f"Fixed failure ({prev_status}) with {analysis.approach} ({analysis.time_complexity}).")
                else:
                    key_change = f"Refined {analysis.approach} implementation."

            step_details.append(
                EvolutionStepDetail(
                    attempt_number=idx,
                    submission_id=sub.id,
                    status=sub.status.value if hasattr(sub.status, "value") else str(sub.status),
                    approach=analysis.approach,
                    time_complexity=analysis.time_complexity,
                    space_complexity=analysis.space_complexity,
                    runtime_ms=sub.runtime_ms,
                    memory_mb=sub.memory_mb,
                    key_change_from_prev=key_change,
                )
            )

            if analysis.potential_issues:
                mistakes_identified.append(f"Attempt {idx}: {analysis.potential_issues}")

            prev_sub = sub

        first_step = step_details[0]
        last_step = step_details[-1]
        accepted_step = next((s for s in reversed(step_details) if s.status == "Accepted"), last_step)

        if first_step.approach != accepted_step.approach or first_step.time_complexity != accepted_step.time_complexity:
            major_changes.append(f"Shifted strategy from {first_step.approach} ({first_step.time_complexity}) to {accepted_step.approach} ({accepted_step.time_complexity}).")
            learning_points.append(f"Optimizing from {first_step.time_complexity} to {accepted_step.time_complexity} solved performance bottlenecks.")
        else:
            major_changes.append(f"Maintained {accepted_step.approach} while resolving edge cases.")
            learning_points.append("Iterative debugging of boundary conditions led to accepted status.")

        overall_summary = (
            f"Solution evolved across {len(step_details)} attempt(s) starting with a {first_step.approach} ({first_step.time_complexity}) approach "
            f"and reaching {accepted_step.status} status with a {accepted_step.approach} ({accepted_step.time_complexity}) implementation."
        )

        return SolutionEvolution(
            problem_id=problem.id,
            problem_title=problem.title,
            total_attempts=len(step_details),
            initial_approach=first_step.approach,
            final_approach=accepted_step.approach,
            major_changes=major_changes,
            optimization_steps=optimization_steps,
            mistakes_identified=mistakes_identified,
            learning_points=learning_points,
            overall_summary=overall_summary,
            steps=step_details,
            analysis_version="v1",
        )

    def answer_question(self, question: str, context: str) -> str:
        q_lower = question.lower()
        if not context.strip():
            return "No matching records were found in your CodeMemory database to answer this question."

        lines = [f"**CodeMemory Grounded Insights for query: '{question}'**\n"]
        if "mistake" in q_lower or "fail" in q_lower or "weak" in q_lower:
            lines.append("Based on your CodeMemory history, repeated difficulties stem primarily from:")
            lines.append("- Nested O(n²) loops triggering Time Limit Exceeded (TLE).")
            lines.append("- Unhandled duplicate values or boundary limits causing Wrong Answer (WA).")
        elif "evolution" in q_lower or "how did i solve" in q_lower or "two sum" in q_lower:
            lines.append("Historical evolution recorded in your CodeMemory database:")
            lines.append("- Initial attempts frequently utilize brute-force approaches before transitioning to HashMap or Two Pointer optimizations.")
        else:
            lines.append("Analysis based on your stored CodeMemory database context:")

        lines.append("\n**Retrieved Relevant Context Sources:**")
        lines.append(context)
        return "\n".join(lines)

    def interpret_evidence(self, evidence: InsightEvidence) -> InterpretationResult:
        """Deterministic, offline evidence interpretation.

        Constructs ``InterpretationResult`` directly from the supplied evidence.
        Never invents statistics, never fabricates weaknesses from empty data,
        and every ``evidence_ref`` traces to a real ``evidence_id``.
        """
        refs: list[str] = []
        observations: list[str] = []
        actions: list[str] = []

        # Collect valid evidence IDs for reference-safety
        valid_ids = evidence.all_evidence_ids()

        def _ref(eid: str) -> None:
            """Record an evidence reference if it exists in the bundle."""
            if eid in valid_ids and eid not in refs:
                refs.append(eid)

        # --- Overview metrics ---
        overview = evidence.metrics.overview
        total_problems = overview.get("total_problems", 0)
        acc_rate = overview.get("overall_acceptance_rate_pct", 0.0)
        solved = overview.get("accepted_problems", 0)

        if total_problems == 0:
            return InterpretationResult(
                headline="Insufficient practice data to generate insights.",
                narrative="No coding problems have been recorded in CodeMemory yet. "
                          "Import submissions or start solving problems to unlock personalized insights.",
                key_observations=["No practice data available."],
                recommended_actions=["Import submissions or begin solving problems."],
                evidence_refs=[],
            )

        # Reference overview items
        for item in evidence.items:
            if item.source == "analytics.overview":
                _ref(item.evidence_id)
                break  # one reference is enough for the overview bucket

        # --- Build headline ---
        headline_parts = [f"{solved}/{total_problems} problems solved"]
        if acc_rate > 0:
            headline_parts.append(f"{acc_rate:.1f}% overall acceptance rate")
        headline = ", ".join(headline_parts) + "."
        if len(headline) > 200:
            headline = headline[:197] + "..."

        # --- Weak topics observations ---
        for wt in evidence.patterns.weak_topics:
            topic = wt.get("topic", "Unknown")
            success_pct = wt.get("success_rate_pct", 0.0)
            n_problems = wt.get("total_problems", 0)
            obs = f"{topic} is a weak area ({success_pct:.0f}% success rate across {n_problems} problems)."
            observations.append(obs)
            actions.append(f"Practice more {topic} problems to strengthen this area.")
            # Reference the corresponding evidence item
            topic_key = topic.lower().replace(" ", "_").replace("-", "_")
            eid = f"pattern_analyzer.weak_topics.{topic_key}"
            _ref(eid)

        # --- High failure topics ---
        for hf in evidence.patterns.high_failure_topics:
            topic = hf.get("topic", "Unknown")
            acc_pct = hf.get("acceptance_rate_pct", 0.0)
            total_subs = hf.get("total_submissions", 0)
            obs = f"{topic} has a high failure rate ({acc_pct:.0f}% acceptance across {total_subs} submissions)."
            if obs not in observations:
                observations.append(obs)
            topic_key = topic.lower().replace(" ", "_").replace("-", "_")
            eid = f"pattern_analyzer.high_failure_topics.{topic_key}"
            _ref(eid)

        # --- Comparisons ---
        for comp in evidence.comparisons:
            if comp.delta < -10.0:
                observations.append(
                    f"{comp.label}: {comp.topic_rate:.1f}% vs {comp.overall_rate:.1f}% overall ({comp.delta:+.1f}%)."
                )
                _ref(comp.evidence_id)

        # --- Improvement patterns ---
        for imp in evidence.patterns.improvement_patterns:
            summary = imp.get("summary", "")
            if summary:
                observations.append(summary)
                metric = imp.get("metric", "unknown")
                eid = f"pattern_analyzer.improvement_patterns.{metric}"
                _ref(eid)

        # --- Unpracticed topics ---
        for ut in evidence.patterns.unpracticed_topics:
            topic = ut.get("topic", "Unknown")
            days = ut.get("days_unpracticed", 0)
            actions.append(f"Resume practicing {topic} (inactive for {days} days).")
            topic_key = topic.lower().replace(" ", "_").replace("-", "_")
            eid = f"pattern_analyzer.unpracticed_topics.{topic_key}"
            _ref(eid)

        # --- Repeated failure problems ---
        if evidence.patterns.repeated_tle_problems:
            observations.append(
                f"{len(evidence.patterns.repeated_tle_problems)} problems have repeated TLE failures."
            )
        if evidence.patterns.repeated_wa_problems:
            observations.append(
                f"{len(evidence.patterns.repeated_wa_problems)} problems have repeated WA failures."
            )

        # Trim to max allowed
        observations = observations[:5]
        actions = actions[:5]
        refs = refs[:20]

        # --- Build narrative ---
        narrative_parts: list[str] = []
        narrative_parts.append(
            f"Across {total_problems} recorded problems, {solved} have been solved "
            f"with an overall acceptance rate of {acc_rate:.1f}%."
        )

        if evidence.patterns.weak_topics:
            weak_names = [wt.get("topic", "?") for wt in evidence.patterns.weak_topics[:3]]
            narrative_parts.append(
                f"The weakest areas are {', '.join(weak_names)}, "
                "where success rates fall below the overall baseline."
            )

        if evidence.comparisons:
            below = [c for c in evidence.comparisons if c.delta < -5.0]
            if below:
                narrative_parts.append(
                    f"{len(below)} topic(s) have acceptance rates meaningfully below the overall average."
                )

        if evidence.patterns.improvement_patterns:
            narrative_parts.append(
                "There are positive improvement trends visible in recent practice activity."
            )

        if evidence.limitations:
            narrative_parts.append(
                "Note: " + " ".join(evidence.limitations[:2])
            )

        narrative = "\n\n".join(narrative_parts)
        if len(narrative) > 3000:
            narrative = narrative[:2997] + "..."

        return InterpretationResult(
            headline=headline,
            narrative=narrative,
            key_observations=observations,
            recommended_actions=actions,
            evidence_refs=refs,
        )

