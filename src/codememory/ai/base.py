"""AI solution analysis provider interface and domain models."""

from codememory.ai.models import SubmissionAnalysis
from codememory.ai.providers.base_provider import BaseAIProvider

# Backward-compatibility type alias
AIAnalysisResult = SubmissionAnalysis

__all__ = ["AIAnalysisResult", "BaseAIProvider", "SubmissionAnalysis"]
