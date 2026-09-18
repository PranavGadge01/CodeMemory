"""Embedding provider abstractions for local-first semantic retrieval."""

from abc import ABC, abstractmethod
import math
import re
from typing import List


class BaseEmbeddingProvider(ABC):
    """Abstract interface for embedding providers."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the vector dimensionality."""
        pass

    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """Embed a single text string into a float vector."""
        pass

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of text strings into float vectors."""
        return [self.embed(t) for t in texts]


class LocalEmbeddingProvider(BaseEmbeddingProvider):
    """Lightweight, local-first vectorizer using feature hashing & term frequency L2-normalized vectors."""

    def __init__(self, dimension: int = 64):
        self._dim = dimension

    @property
    def dimension(self) -> int:
        return self._dim

    def _tokenize(self, text: str) -> List[str]:
        tokens = re.findall(r"\w+", (text or "").lower())
        # Generate unigrams and bigrams
        bigrams = [f"{tokens[i]}_{tokens[i+1]}" for i in range(len(tokens) - 1)]
        return tokens + bigrams

    def embed(self, text: str) -> List[float]:
        vec = [0.0] * self._dim
        tokens = self._tokenize(text)
        if not tokens:
            return vec

        for tok in tokens:
            # Hash token into dimension index
            idx = abs(hash(tok)) % self._dim
            vec[idx] += 1.0

        # L2 Normalize
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0.0:
            vec = [v / norm for v in vec]

        return vec


class MockEmbeddingProvider(BaseEmbeddingProvider):
    """Mock embedding provider for unit tests."""

    def __init__(self, dimension: int = 32):
        self._dim = dimension

    @property
    def dimension(self) -> int:
        return self._dim

    def embed(self, text: str) -> List[float]:
        val = (len(text or "") % 10) / 10.0
        vec = [val] * self._dim
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0.0:
            vec = [v / norm for v in vec]
        return vec
