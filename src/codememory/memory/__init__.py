"""CodeMemory Personal Memory & Intelligent Retrieval package."""

from codememory.memory.embeddings import BaseEmbeddingProvider, LocalEmbeddingProvider, MockEmbeddingProvider
from codememory.memory.index import SemanticIndex
from codememory.memory.models import MemoryDocument, MemoryResult, MemoryType, SimilarProblemResult
from codememory.memory.pipeline import DocumentPipeline
from codememory.memory.retriever import HybridRetriever
from codememory.memory.service import MemoryService

__all__ = [
    "BaseEmbeddingProvider",
    "DocumentPipeline",
    "HybridRetriever",
    "LocalEmbeddingProvider",
    "MemoryDocument",
    "MemoryResult",
    "MemoryService",
    "MemoryType",
    "MockEmbeddingProvider",
    "SemanticIndex",
    "SimilarProblemResult",
]
