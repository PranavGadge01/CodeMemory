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

