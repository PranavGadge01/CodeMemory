"""Personal DSA Memory Service for intelligent semantic retrieval, similarity, and mistake tracking."""

from pathlib import Path
from typing import Any, Dict, List, Optional
from codememory.ai.analyzer import AICodeAnalyzer
from codememory.domain.enums import SubmissionStatus
from codememory.domain.models import Problem
from codememory.memory.embeddings import BaseEmbeddingProvider, LocalEmbeddingProvider
from codememory.memory.index import SemanticIndex
from codememory.memory.models import MemoryDocument, MemoryResult, MemoryType, SimilarProblemResult
from codememory.memory.pipeline import DocumentPipeline
from codememory.memory.retriever import HybridRetriever


class MemoryService:
    """Master personal memory service managing indexing, hybrid retrieval, similarity, and provenance tracking."""

    def __init__(
        self,
        storage: Any,
        base_dir: str | Path = "data",
        embedding_provider: Optional[BaseEmbeddingProvider] = None,
        ai_analyzer: Optional[AICodeAnalyzer] = None,
    ):
        self.storage = storage
        self.base_dir = Path(base_dir)
        self.embedding_provider = embedding_provider or LocalEmbeddingProvider()
        self.ai_analyzer = ai_analyzer
        self.pipeline = DocumentPipeline(ai_analyzer=self.ai_analyzer)
        self.index = SemanticIndex(data_dir=self.base_dir)
        self.retriever = HybridRetriever(index=self.index, embedding_provider=self.embedding_provider)

        # Cache of memory documents in memory
        self._doc_cache: List[MemoryDocument] = []
        self._doc_map: Dict[str, MemoryDocument] = {}

    @staticmethod
    def _filter_problems_by_account(
        problems: List[Problem], account: str | None
    ) -> List[Problem]:
        """Filter a list of problems so that only submissions belonging to ``account`` are retained.

        When ``account`` is None, LeetCode-sourced submissions (those with a
        non-None ``source_provider``) are stripped — matching the isolation
        contract of ``CodeMemoryService.list_problems``. Problems that become
        empty after filtering are excluded entirely.
        """
        from codememory.domain.enums import Platform

        if account is None:
            # No active account: exclude problems with ONLY LeetCode-sourced submissions.
            filtered: list[Problem] = []
            for p in problems:
                has_non_leetcode = False
                kept_attempts = []
                for a in p.attempts:
                    non_leetcode = [s for s in a.submissions if s.source_provider is None]
                    if non_leetcode:
                        has_non_leetcode = True
                        import copy
                        a_copy = copy.copy(a)
                        a_copy.submissions = non_leetcode
                        kept_attempts.append(a_copy)
                if has_non_leetcode:
                    import copy
                    p_copy = copy.copy(p)
                    p_copy.attempts = kept_attempts
                    filtered.append(p_copy)
            return filtered

        # Account provided: keep only submissions from that account.
        filtered = []
        for p in problems:
            kept_attempts = []
            for a in p.attempts:
                matching = [s for s in a.submissions if s.source_account == account]
                if matching:
                    import copy
                    a_copy = copy.copy(a)
                    a_copy.submissions = matching
                    kept_attempts.append(a_copy)
            if kept_attempts:
                import copy
                p_copy = copy.copy(p)
                p_copy.attempts = kept_attempts
                filtered.append(p_copy)
        return filtered

    def index_all(
        self, force_rebuild: bool = False, account: str | None = None
    ) -> Dict[str, int]:
        """Perform incremental semantic vector indexing over stored CodeMemory problems.

        When ``account`` is provided, only documents whose submission belongs to
        that account are indexed. When ``account`` is None, LeetCode-sourced
        documents are excluded to prevent cross-account memory leakage.
        """
        problems: List[Problem] = list(self.storage.list_all())
        problems = self._filter_problems_by_account(problems, account)
        docs = self.pipeline.extract_documents(problems)

        if force_rebuild:
            self.index.clear()

        indexed_count = 0
        skipped_count = 0

        for doc in docs:
            # Check incremental indexing status
            if not force_rebuild and self.index.is_indexed(doc.memory_id, doc.content_hash):
                skipped_count += 1
            else:
                # If indexing with an account, only index docs from that account.
                # Documents without source_account are still indexed (legacy/manual).
                if account is not None and doc.source_account is not None and doc.source_account != account:
                    skipped_count += 1
                    continue
                vector = self.embedding_provider.embed(f"{doc.title} {doc.content}")
                self.index.add(doc, vector)
                indexed_count += 1

        self.index.save()
        self._doc_cache = docs
        self._doc_map = {d.memory_id: d for d in docs}

        return {
            "total_documents": len(docs),
            "indexed": indexed_count,
            "skipped": skipped_count,
            "vector_count": self.index.count(),
        }

    def _ensure_indexed(self, account: str | None = None) -> List[MemoryDocument]:
        """Ensure documents are extracted and in-memory cache is populated.

        When ``account`` is provided, only documents matching that account
        (or with no account set) are cached.
        """
        if not self._doc_cache:
            problems = list(self.storage.list_all())
            problems = self._filter_problems_by_account(problems, account)
            self._doc_cache = self.pipeline.extract_documents(problems)
            self._doc_map = {d.memory_id: d for d in self._doc_cache}
        if account is not None:
            return [d for d in self._doc_cache if d.source_account is None or d.source_account == account]
        return self._doc_cache

    def search(
        self,
        query: str,
        filters: Optional[Dict[str, str]] = None,
        top_k: int = 10,
        account: str | None = None,
    ) -> List[MemoryResult]:
        """Perform hybrid search over CodeMemory documents.

        When ``account`` is provided, only documents from that account are
        searched. LeetCode-sourced documents from other accounts are excluded.
        """
        docs = self._ensure_indexed(account=account)
        if self.index.count() == 0 and docs:
            self.index_all(force_rebuild=False, account=account)
        return self.retriever.search(
            query=query, documents=docs, filters=filters, top_k=top_k, account=account
        )

    def find_similar_problem(
        self, problem_id: str, top_k: int = 5, account: str | None = None
    ) -> List[SimilarProblemResult]:
        """Find problems similar to a given problem based on topics, patterns, and semantic similarity.

        When ``account`` is provided, only problems with submissions from that
        account are considered as candidates. Problem metadata (title,
        difficulty, topics) may still be globally visible — only user-specific
        attempt/submission history is isolated.
        """
        docs = self._ensure_indexed(account=account)
        target_prob = self.storage.get_by_id(problem_id) or self.storage.get_by_slug(problem_id)
        if not target_prob:
            return []

        # Verify the target problem belongs to the account
        if account is not None:
            target_has_account = any(
                s.source_account == account
                for a in target_prob.attempts
                for s in a.submissions
            )
            if not target_has_account:
                return []

        target_doc = next((d for d in docs if d.problem_id == target_prob.id and d.memory_type == MemoryType.PROBLEM), None)
        target_text = f"{target_prob.title} {', '.join(target_prob.topics)} {target_prob.statement or ''}"

        all_problems = [p for p in self.storage.list_all() if p.id != target_prob.id]
        if account is not None:
            all_problems = [
                p for p in all_problems
                if any(s.source_account == account for a in p.attempts for s in a.submissions)
            ]

        results: List[SimilarProblemResult] = []

        target_topics = set(t.lower() for t in target_prob.topics)

        for p in all_problems:
            p_topics = set(t.lower() for t in p.topics)
            shared_topics = list(target_topics.intersection(p_topics))

            # Semantic similarity score
            v1 = self.embedding_provider.embed(target_text)
            p_text = f"{p.title} {', '.join(p.topics)} {p.statement or ''}"
            v2 = self.embedding_provider.embed(p_text)

            sim_score = sum(a * b for a, b in zip(v1, v2))

            reasons = []
            if shared_topics:
                reasons.append(f"Shared topics: {', '.join(shared_topics)}")
            if p.difficulty == target_prob.difficulty:
                reasons.append(f"Same difficulty ({p.difficulty.value if hasattr(p.difficulty, 'value') else p.difficulty})")
            if sim_score > 0.4:
                reasons.append("Conceptual & structural similarity")

            if not reasons:
                reasons.append("Algorithmic categorization similarity")

            results.append(
                SimilarProblemResult(
                    problem_id=p.id,
                    title=p.title,
                    difficulty=p.difficulty.value if hasattr(p.difficulty, "value") else str(p.difficulty),
                    similarity_score=round(sim_score, 4),
                    shared_topics=shared_topics,
                    shared_patterns=[],
                    explanation=" • ".join(reasons),
                )
            )

        results.sort(key=lambda r: (len(r.shared_topics), r.similarity_score), reverse=True)
        return results[:top_k]

    def find_common_mistakes(
        self, topic: Optional[str] = None, account: str | None = None
    ) -> List[MemoryResult]:
        """Retrieve actual historical mistake evidence and failed attempt memory documents.

        When ``account`` is provided, only mistake/AI analysis documents from
        that account are returned.
        """
        docs = self._ensure_indexed(account=account)
        mistake_docs = [d for d in docs if d.memory_type in (MemoryType.MISTAKE, MemoryType.AI_ANALYSIS)]

        if topic:
            top_clean = topic.lower()
            mistake_docs = [d for d in mistake_docs if any(top_clean in t.lower() for t in d.topics)]

        query = f"mistake failure bug TLE WA wrong answer {topic or ''}"
        return self.retriever.search(
            query=query, documents=mistake_docs, top_k=10, account=account
        )

    def find_previous_approaches(
        self, problem_id: str, account: str | None = None
    ) -> List[Dict[str, Any]]:
        """Retrieve chronological approach progression and attempt outcomes for a problem.

        When ``account`` is provided, only submissions from that account are
        included in the returned history. Problem metadata (title, attempts)
        may still be visible from other accounts — only submissions are filtered.
        """
        prob = self.storage.get_by_id(problem_id) or self.storage.get_by_slug(problem_id)
        if not prob or not prob.attempts:
            return []

        history = []
        for att in sorted(prob.attempts, key=lambda a: a.attempt_number):
            if account is not None:
                subs = [s for s in att.submissions if s.source_account == account]
            else:
                subs = att.submissions

            if not subs:
                continue

            status_str = att.status.value if hasattr(att.status, "value") else str(att.status)
            history.append(
                {
                    "attempt_number": att.attempt_number,
                    "attempt_id": att.id,
                    "status": status_str,
                    "approach": att.approach_summary or "Standard Approach",
                    "reasoning": att.reasoning,
                    "time_complexity": att.analysis.time_complexity if att.analysis else None,
                    "space_complexity": att.analysis.space_complexity if att.analysis else None,
                    "submissions_count": len(subs),
                    "created_at": att.created_at.strftime("%Y-%m-%d %H:%M UTC"),
                }
            )
        return history

    def get_memory_stats(self, account: str | None = None) -> Dict[str, Any]:
        """Compute summary statistics of stored memory documents and indexed vectors.

        When ``account`` is provided, stats are scoped to that account's
        documents.
        """
        docs = self._ensure_indexed(account=account)
        type_counts: Dict[str, int] = {}
        for d in docs:
            type_counts[d.memory_type.value] = type_counts.get(d.memory_type.value, 0) + 1

        return {
            "total_documents": len(docs),
            "indexed_vectors": self.index.count(),
            "type_counts": type_counts,
            "unique_problems": len(set(d.problem_id for d in docs)),
        }
