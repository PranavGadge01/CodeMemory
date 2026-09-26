"""Abstract interface for AI analysis providers."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional, List

from pydantic import BaseModel, Field

from codememory.ai.models import SubmissionAnalysis, SolutionEvolution
from codememory.domain.models import Problem, Submission

if TYPE_CHECKING:
    from codememory.ai.evidence_models import InsightEvidence


class InterpretationResult(BaseModel):
    """Structured AI interpretation output.

    Providers return this directly — there is no prose-parsing step.
    Every ``evidence_refs`` entry must correspond to an ``evidence_id``
    present in the source ``InsightEvidence`` bundle.
    """

    headline: str = Field(max_length=200, description="One-sentence summary")
    narrative: str = Field(max_length=3000, description="Multi-paragraph interpretation")
    key_observations: list[str] = Field(default_factory=list, max_length=5)
    recommended_actions: list[str] = Field(default_factory=list, max_length=5)
    evidence_refs: list[str] = Field(default_factory=list, max_length=20)


class BaseAIProvider(ABC):
    """Abstract interface for AI providers analyzing submissions and answering grounded questions."""

    @abstractmethod
    def analyze_submission(
        self,
        submission: Submission,
        problem: Problem,
        previous_submission: Optional[Submission] = None,
    ) -> SubmissionAnalysis:
        """Analyze a submission attempt and return structured submission analysis."""
        pass

    @abstractmethod
    def analyze_evolution(
        self,
        problem: Problem,
        submissions: List[Submission],
    ) -> SolutionEvolution:
        """Analyze the evolution across multiple submission attempts for a problem."""
        pass

    @abstractmethod
    def answer_question(
        self,
        question: str,
        context: str,
    ) -> str:
        """Answer a question grounded in the provided CodeMemory context."""
        pass

    @abstractmethod
    def interpret_evidence(
        self,
        evidence: "InsightEvidence",
    ) -> InterpretationResult:
        """Interpret structured deterministic evidence into a grounded insight.

        The provider must NOT invent statistics, create new evidence, perform
        independent analytics, or reference evidence IDs not present in the
        supplied evidence bundle.
        """
        pass


def serialize_evidence(evidence: "InsightEvidence") -> str:
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


