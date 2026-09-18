"""HybridRetriever combining structured criteria, keyword TF-IDF matching, and semantic vector similarity."""

import math
import re
from typing import Dict, List, Optional
from codememory.memory.embeddings import BaseEmbeddingProvider, LocalEmbeddingProvider
from codememory.memory.index import SemanticIndex
from codememory.memory.models import MemoryDocument, MemoryResult, MemoryType


class HybridRetriever:
    """Retrieves ranked MemoryResult items combining structured filters, keyword relevance, and vector similarity."""

    def __init__(
        self,
        index: SemanticIndex,
        embedding_provider: Optional[BaseEmbeddingProvider] = None,
        semantic_weight: float = 0.5,
        keyword_weight: float = 0.3,
        structured_weight: float = 0.2,
    ):
        self.index = index
        self.embedding_provider = embedding_provider or LocalEmbeddingProvider()
        self.semantic_weight = semantic_weight
        self.keyword_weight = keyword_weight
        self.structured_weight = structured_weight

    def _compute_keyword_score(self, query: str, doc: MemoryDocument) -> float:
        """Compute term frequency keyword match score."""
        q_tokens = set(re.findall(r"\w+", (query or "").lower()))
        if not q_tokens:
            return 0.0

        doc_text = f"{doc.title} {doc.content} {' '.join(doc.topics)} {' '.join(doc.patterns)}".lower()
        doc_tokens = re.findall(r"\w+", doc_text)

        if not doc_tokens:
            return 0.0

        matches = sum(1 for tok in q_tokens if tok in doc_tokens)
        title_matches = sum(1 for tok in q_tokens if tok in doc.title.lower())

        # Give title matches double weight
        raw_score = (matches + title_matches * 2) / (len(q_tokens) * 3)
        return min(1.0, raw_score)

    def _compute_structured_score(self, filters: Dict[str, str], doc: MemoryDocument) -> float:
        """Compute structured filter match score."""
        if not filters:
            return 1.0

        matches = 0
        total = len(filters)

        for k, v in filters.items():
            v_clean = str(v).lower().strip()
            if k == "difficulty" and doc.difficulty.lower() == v_clean:
                matches += 1
            elif k == "topic" and any(v_clean in t.lower() for t in doc.topics):
                matches += 1
            elif k == "pattern" and any(v_clean in p.lower() for p in doc.patterns):
                matches += 1
            elif k == "status" and doc.status.lower() == v_clean:
                matches += 1
            elif k == "language" and doc.language.lower() == v_clean:
                matches += 1
            elif k == "memory_type" and doc.memory_type.value.lower() == v_clean:
                matches += 1
            elif k == "problem_id" and doc.problem_id == v:
                matches += 1

        return matches / total if total > 0 else 1.0

    def search(
        self,
        query: str,
        documents: List[MemoryDocument],
        filters: Optional[Dict[str, str]] = None,
        top_k: int = 10,
    ) -> List[MemoryResult]:
        """Perform hybrid retrieval over a collection of MemoryDocuments."""
        if not documents:
            return []

        doc_map: Dict[str, MemoryDocument] = {d.memory_id: d for d in documents}

        # 1. Semantic Similarity Scores
        q_vector = self.embedding_provider.embed(query) if query else []
        semantic_scores: Dict[str, float] = {}
        if q_vector and self.index.count() > 0:
            raw_semantic = self.index.search(q_vector, top_k=len(documents))
            semantic_scores = {m_id: score for m_id, score in raw_semantic}

        results: List[MemoryResult] = []

        for doc in documents:
            # Check structured filters if mandatory matching requested
            if filters and "memory_type" in filters and filters["memory_type"].lower() != doc.memory_type.value.lower():
                continue
            if filters and "problem_id" in filters and filters["problem_id"] != doc.problem_id:
                continue

            k_score = self._compute_keyword_score(query, doc)
            s_score = semantic_scores.get(doc.memory_id, 0.0)
            st_score = self._compute_structured_score(filters or {}, doc)

            # Combined hybrid score
            final_score = (
                s_score * self.semantic_weight
                + k_score * self.keyword_weight
                + st_score * self.structured_weight
            )

            # Format snippet
            snippet = doc.content[:250].replace("\n", " ") + ("..." if len(doc.content) > 250 else "")

            results.append(
                MemoryResult(
                    memory_id=doc.memory_id,
                    score=round(final_score, 4),
                    memory_type=doc.memory_type,
                    problem_id=doc.problem_id,
                    title=doc.title,
                    snippet=snippet,
                    content=doc.content,
                    topics=doc.topics,
                    patterns=doc.patterns,
                    difficulty=doc.difficulty,
                    status=doc.status,
                    source=doc.source,
                    source_reference=doc.source_reference,
                    explanation=f"Hybrid score: {final_score:.2f} (Semantic: {s_score:.2f}, Keyword: {k_score:.2f}, Structured: {st_score:.2f})",
                )
            )

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]
