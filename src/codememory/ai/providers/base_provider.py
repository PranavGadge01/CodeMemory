"""Abstract interface for AI analysis providers."""

from abc import ABC, abstractmethod
from typing import Optional, List
from codememory.ai.models import SubmissionAnalysis, SolutionEvolution
from codememory.domain.models import Problem, Submission


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
