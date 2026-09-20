"""Insight service orchestrating the grounded personalized insight pipeline.

Pipeline:

    EvidenceBuilder  →  InsightEvidence  →  AI Provider  →  InterpretationResult
                                                              ↓
                                                       EvidenceValidator
                                                              ↓
                                                       GroundedInsight

The AI interprets evidence produced by CodeMemory; it does not produce or
independently calculate the underlying evidence.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from codememory.ai.evidence_builder import EvidenceBuilder
from codememory.ai.evidence_models import InsightEvidence
from codememory.ai.evidence_validator import EvidenceValidationError, EvidenceValidator
from codememory.ai.providers.base_provider import BaseAIProvider, InterpretationResult

if TYPE_CHECKING:
    pass


class GroundedInsight(BaseModel):
    """Final grounded insight with full provenance chain.

    - ``evidence_id`` identifies the source ``InsightEvidence`` bundle.
    - ``evidence_refs`` lists the specific ``evidence_id``s from that bundle
      that the AI interpretation referenced.
    - ``confidence_notes`` surfaces any sample-size limitations from the
      evidence.
    """

    scope: str
    generated_at: datetime
    headline: str
    narrative: str
    key_observations: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    evidence_summary: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    confidence_notes: list[str] = Field(default_factory=list)
    evidence_id: str = Field(description="The InsightEvidence.evidence_id this insight was built from")


class InsightService:
    """Orchestrates the grounded insight pipeline.

    1. Builds ``InsightEvidence`` via the ``EvidenceBuilder``.
    2. Builds ``evidence_summary`` deterministically (no AI).
    3. Calls ``ai_provider.interpret_evidence(evidence)`` → ``InterpretationResult``.
    4. Validates the result with ``EvidenceValidator``.
    5. Assembles ``GroundedInsight``.

    On validation failure the service falls back to producing a minimal
    insight from the evidence summary alone, rather than surfacing an
    unvalidated interpretation.
    """

    def __init__(
        self,
        ai_provider: BaseAIProvider,
        evidence_builder: EvidenceBuilder,
    ):
        self.ai_provider = ai_provider
        self.evidence_builder = evidence_builder
        self._validator = EvidenceValidator()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_full_profile_insight(self) -> GroundedInsight:
        """Generate a grounded insight covering the user's full practice profile."""
        evidence = self.evidence_builder.build_full_profile_evidence()
        return self._interpret_and_assemble(evidence)

    def generate_topic_insight(self, topic: str) -> GroundedInsight:
        """Generate a grounded insight focused on a specific DSA topic."""
        evidence = self.evidence_builder.build_topic_evidence(topic)
        return self._interpret_and_assemble(evidence)

    def generate_problem_insight(self, problem_identifier: str) -> GroundedInsight:
        """Generate a grounded insight focused on a specific problem."""
        evidence = self.evidence_builder.build_problem_evidence(problem_identifier)
        return self._interpret_and_assemble(evidence)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _interpret_and_assemble(self, evidence: InsightEvidence) -> GroundedInsight:
        """Interpret evidence through the AI provider, validate, and assemble the final insight."""
        evidence_summary = self._build_evidence_summary(evidence)

        # Get AI interpretation
        interpretation = self.ai_provider.interpret_evidence(evidence)

        # Validate provenance: evidence_refs ⊆ evidence.all_evidence_ids()
        try:
            self._validator.validate(evidence, interpretation)
        except EvidenceValidationError:
            # Provider returned invalid refs — fall back to evidence summary
            interpretation = InterpretationResult(
                headline="Practice overview based on recorded evidence.",
                narrative=evidence_summary,
                key_observations=[],
                recommended_actions=[],
                evidence_refs=[],
            )

        return GroundedInsight(
            scope=evidence.scope,
            generated_at=evidence.generated_at,
            headline=interpretation.headline,
            narrative=interpretation.narrative,
            key_observations=interpretation.key_observations,
            recommended_actions=interpretation.recommended_actions,
            evidence_summary=evidence_summary,
            evidence_refs=interpretation.evidence_refs,
            confidence_notes=list(evidence.limitations),
            evidence_id=evidence.evidence_id,
        )

    @staticmethod
    def _build_evidence_summary(evidence: InsightEvidence) -> str:
        """Build a deterministic, human-readable summary of the evidence.

        This is pure string formatting of evidence items — no AI involved.
        """
        parts: list[str] = []

        # Overview
        overview = evidence.metrics.overview
        total = overview.get("total_problems", 0)
        solved = overview.get("accepted_problems", 0)
        acc_rate = overview.get("overall_acceptance_rate_pct", 0.0)
        if total > 0:
            parts.append(f"Profile: {solved}/{total} problems solved, {acc_rate:.1f}% acceptance rate.")

        # Topic highlights
        for ts in evidence.metrics.topic_stats[:5]:
            topic = ts.get("topic", "?")
            t_rate = ts.get("acceptance_rate_pct", 0.0)
            t_count = ts.get("total_problems", 0)
            parts.append(f"  {topic}: {t_rate:.1f}% acceptance ({t_count} problems)")

        # Key comparisons
        for comp in evidence.comparisons[:5]:
            if abs(comp.delta) >= 5.0:
                parts.append(f"  {comp.label}: {comp.delta:+.1f}%")

        # Patterns
        if evidence.patterns.weak_topics:
            weak_names = [wt.get("topic", "?") for wt in evidence.patterns.weak_topics[:3]]
            parts.append(f"Weak topics: {', '.join(weak_names)}")

        # Limitations
        for lim in evidence.limitations:
            parts.append(f"Note: {lim}")

        return "\n".join(parts) if parts else "No evidence available."
