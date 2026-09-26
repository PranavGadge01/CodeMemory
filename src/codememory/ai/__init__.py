"""AI Analysis & Personal DSA Memory package."""

from codememory.ai.analyzer import AICodeAnalyzer, compute_code_hash
from codememory.ai.base import AIAnalysisResult, BaseAIProvider
from codememory.ai.context_builder import ContextBuilder
from codememory.ai.evidence_builder import EvidenceBuilder
from codememory.ai.evidence_models import EvidenceComparison, EvidenceItem, InsightEvidence
from codememory.ai.evidence_validator import EvidenceValidationError, EvidenceValidator
from codememory.ai.evolution_service import EvolutionService, EvolutionSummary
from codememory.ai.fallback_provider import HeuristicAIProvider
from codememory.ai.insight_service import GroundedInsight, InsightService
from codememory.ai.memory_service import MemoryService
from codememory.ai.models import AIAnalysisRecord, SolutionEvolution, SubmissionAnalysis
from codememory.ai.providers import OpenAIProvider, Qwen3Provider, get_ai_provider
from codememory.ai.providers.base_provider import InterpretationResult

__all__ = [
    "AICodeAnalyzer",
    "AIAnalysisResult",
    "BaseAIProvider",
    "ContextBuilder",
    "EvidenceBuilder",
    "EvidenceComparison",
    "EvidenceItem",
    "EvidenceValidationError",
    "EvidenceValidator",
    "EvolutionService",
    "EvolutionSummary",
    "GroundedInsight",
    "HeuristicAIProvider",
    "InsightEvidence",
    "InsightService",
    "InterpretationResult",
    "MemoryService",
    "AIAnalysisRecord",
    "SolutionEvolution",
    "SubmissionAnalysis",
    "OpenAIProvider",
    "Qwen3Provider",
    "get_ai_provider",
    "compute_code_hash",
]

