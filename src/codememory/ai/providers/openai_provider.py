"""OpenAI API provider implementation with structured Pydantic output validation and offline fallback."""

import json
import os
from typing import List, Optional
from pydantic import ValidationError

from codememory.ai.models import SubmissionAnalysis, SolutionEvolution
from codememory.ai.prompts import (
    SYSTEM_ASK_CODEMEMORY_PROMPT,
    SYSTEM_EVOLUTION_ANALYSIS_PROMPT,
    SYSTEM_INTERPRET_EVIDENCE_PROMPT,
    SYSTEM_SUBMISSION_ANALYSIS_PROMPT,
    USER_ASK_CODEMEMORY_PROMPT,
    USER_EVOLUTION_ANALYSIS_PROMPT,
    USER_INTERPRET_EVIDENCE_PROMPT,
    USER_SUBMISSION_ANALYSIS_PROMPT,
)
from codememory.ai.providers.base_provider import BaseAIProvider, InterpretationResult
from codememory.ai.providers.heuristic_provider import HeuristicAIProvider
from codememory.domain.models import Problem, Submission

from codememory.ai.evidence_models import InsightEvidence


class OpenAIProvider(BaseAIProvider):
    """OpenAI API-backed provider for structured solution analysis and grounded QA."""

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gpt-4o-mini"):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model_name = model_name
        self.ai_enabled = os.environ.get("AI_ENABLED", "true").lower() in ("true", "1", "yes")
        self.fallback = HeuristicAIProvider()

    def is_available(self) -> bool:
        """Check if AI is enabled and an API key is configured."""
        return bool(self.ai_enabled and self.api_key)

    def analyze_submission(
        self,
        submission: Submission,
        problem: Problem,
        previous_submission: Optional[Submission] = None,
    ) -> SubmissionAnalysis:
        if not self.is_available():
            return self.fallback.analyze_submission(submission, problem, previous_submission)

        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)

            prev_ctx = "None"
            if previous_submission:
                prev_ctx = f"Status: {previous_submission.status.value}, Code: {previous_submission.code[:200]}..."

            prompt = USER_SUBMISSION_ANALYSIS_PROMPT.format(
                problem_title=problem.title,
                difficulty=problem.difficulty.value if hasattr(problem.difficulty, "value") else str(problem.difficulty),
                topics=", ".join(problem.topics) if problem.topics else "None",
                statement=problem.statement or "Not provided",
                status=submission.status.value if hasattr(submission.status, "value") else str(submission.status),
                language=submission.language,
                runtime_ms=f"{submission.runtime_ms:.1f}" if submission.runtime_ms is not None else "N/A",
                memory_mb=f"{submission.memory_mb:.1f}" if submission.memory_mb is not None else "N/A",
                error_message=submission.error_message or "None",
                code=submission.code or "",
                previous_context=prev_ctx,
            )

            response = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_SUBMISSION_ANALYSIS_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )

            content = response.choices[0].message.content or "{}"
            raw_data = json.loads(content)
            return SubmissionAnalysis.model_validate(raw_data)

        except Exception:
            # On network error, invalid key, rate limit, or malformed json -> fall back safely
            return self.fallback.analyze_submission(submission, problem, previous_submission)

    def analyze_evolution(
        self,
        problem: Problem,
        submissions: List[Submission],
    ) -> SolutionEvolution:
        if not self.is_available() or not submissions:
            return self.fallback.analyze_evolution(problem, submissions)

        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)

            sorted_subs = sorted(submissions, key=lambda s: s.submitted_at)
            attempts_formatted = "\n".join(
                f"Attempt {idx} ({s.status.value}): Code length {len(s.code or '')} chars, Runtime {s.runtime_ms or 'N/A'} ms\n```\n{s.code[:300]}\n```"
                for idx, s in enumerate(sorted_subs, start=1)
            )

            prompt = USER_EVOLUTION_ANALYSIS_PROMPT.format(
                problem_id=problem.id,
                problem_title=problem.title,
                total_attempts=len(sorted_subs),
                attempts_formatted=attempts_formatted,
            )

            response = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_EVOLUTION_ANALYSIS_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )

            content = response.choices[0].message.content or "{}"
            raw_data = json.loads(content)

            # Ensure steps from fallback are included if missing in LLM response
            evolution = SolutionEvolution.model_validate(raw_data)
            if not evolution.steps:
                fallback_evo = self.fallback.analyze_evolution(problem, submissions)
                evolution.steps = fallback_evo.steps
            return evolution

        except Exception:
            return self.fallback.analyze_evolution(problem, submissions)

    def answer_question(self, question: str, context: str) -> str:
        if not self.is_available():
            return self.fallback.answer_question(question, context)

        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)

            prompt = USER_ASK_CODEMEMORY_PROMPT.format(question=question, context=context)

            response = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_ASK_CODEMEMORY_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
            )

            return response.choices[0].message.content or "No response generated."
        except Exception:
            return self.fallback.answer_question(question, context)

    # ------------------------------------------------------------------
    # Evidence interpretation
    # ------------------------------------------------------------------

    def interpret_evidence(self, evidence: InsightEvidence) -> InterpretationResult:
        """Interpret structured evidence using the OpenAI API.

        Serializes the evidence into a human-readable prompt with embedded
        evidence IDs, requests structured JSON matching ``InterpretationResult``,
        validates with Pydantic, and falls back to the heuristic provider on
        any API, parsing, schema, or validation failure.
        """
        if not self.is_available():
            return self.fallback.interpret_evidence(evidence)

        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)

            evidence_text = self._serialize_evidence(evidence)
            prompt = USER_INTERPRET_EVIDENCE_PROMPT.format(evidence_text=evidence_text)

            response = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_INTERPRET_EVIDENCE_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )

            content = response.choices[0].message.content or "{}"
            raw_data = json.loads(content)
            result = InterpretationResult.model_validate(raw_data)

            # Validate evidence references: strip any IDs the model hallucinated
            valid_ids = evidence.all_evidence_ids()
            result.evidence_refs = [ref for ref in result.evidence_refs if ref in valid_ids]

            return result

        except Exception:
            return self.fallback.interpret_evidence(evidence)

    @staticmethod
    def _serialize_evidence(evidence: InsightEvidence) -> str:
        """Serialize InsightEvidence into a compact, human-readable text with evidence IDs."""
        lines: list[str] = []
        lines.append(f"EVIDENCE BUNDLE (scope: {evidence.scope})")
        lines.append("")

        # Metrics overview
        if evidence.metrics.overview:
            lines.append("OVERVIEW METRICS:")
            for item in evidence.items:
                if item.source == "analytics.overview":
                    unit_str = f" {item.unit}" if item.unit else ""
                    lines.append(f"  [{item.evidence_id}] {item.label}: {item.value}{unit_str}")
            lines.append("")

        # Topic statistics
        topic_items = [i for i in evidence.items if i.source.startswith("analytics.topic_stats")]
        if topic_items:
            lines.append("TOPIC STATISTICS:")
            for item in topic_items:
                unit_str = f" {item.unit}" if item.unit else ""
                sample = f" (sample: {item.sample_size})" if item.sample_size is not None else ""
                lines.append(f"  [{item.evidence_id}] {item.label}: {item.value}{unit_str}{sample}")
            lines.append("")

        # Difficulty statistics
        diff_items = [i for i in evidence.items if i.source.startswith("analytics.difficulty_stats")]
        if diff_items:
            lines.append("DIFFICULTY STATISTICS:")
            for item in diff_items:
                unit_str = f" {item.unit}" if item.unit else ""
                lines.append(f"  [{item.evidence_id}] {item.label}: {item.value}{unit_str}")
            lines.append("")

        # Comparisons
        if evidence.comparisons:
            lines.append("COMPARISONS:")
            for comp in evidence.comparisons:
                lines.append(
                    f"  [{comp.evidence_id}] {comp.label}: "
                    f"{comp.topic_rate:.1f}% vs {comp.overall_rate:.1f}% (delta: {comp.delta:+.1f}%)"
                )
            lines.append("")

        # Patterns
        pattern_items = [i for i in evidence.items if i.source.startswith("pattern_analyzer")]
        if pattern_items:
            lines.append("PATTERNS:")
            for item in pattern_items:
                lines.append(f"  [{item.evidence_id}] {item.label}: {item.value}")
            lines.append("")

        # AI analysis snapshots
        ai_items = [i for i in evidence.items if i.source_type == "ai_analysis"]
        if ai_items:
            lines.append("AI ANALYSIS SNAPSHOTS:")
            for item in ai_items:
                lines.append(f"  [{item.evidence_id}] {item.label}: {item.value}")
            lines.append("")

        # Supporting problems
        if evidence.supporting_problems:
            lines.append("SUPPORTING PROBLEMS:")
            for ps in evidence.supporting_problems:
                lines.append(
                    f"  {ps.title} ({ps.difficulty}) — {ps.status}, "
                    f"{ps.total_attempts} attempts, topics: {', '.join(ps.topics)}"
                )
            lines.append("")

        # Limitations
        if evidence.limitations:
            lines.append("LIMITATIONS:")
            for lim in evidence.limitations:
                lines.append(f"  - {lim}")

        return "\n".join(lines)

