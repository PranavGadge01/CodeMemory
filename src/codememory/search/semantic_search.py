"""Lightweight local semantic search engine using TF-IDF vector similarity."""

import math
import re
from collections import Counter
from typing import List, Dict, Tuple, Optional
from pydantic import BaseModel
from codememory.domain.models import Problem, Submission


class SemanticSearchResult(BaseModel):
    """Result item from semantic query search."""

    problem: Problem
    relevance_score: float
    matched_snippet: str
    match_reason: str


class LocalSemanticSearchEngine:
    """Standalone local TF-IDF & vector similarity search engine."""

    def __init__(self):
        self._document_vectors: Dict[str, Dict[str, float]] = {}
        self._document_texts: Dict[str, str] = {}
        self._df: Counter = Counter()  # Document Frequency
        self._num_docs: int = 0
        self._problems_map: Dict[str, Problem] = {}
        self._submissions_map: Dict[str, List[Submission]] = {}

    def index_dataset(self, problems: List[Problem], submissions: List[Submission]) -> None:
        """Build TF-IDF inverted index over problems and historical attempts."""
        self._document_vectors.clear()
        self._document_texts.clear()
        self._df.clear()
        self._problems_map.clear()
        self._submissions_map.clear()

        # Group submissions by problem_id
        for sub in submissions:
            self._submissions_map.setdefault(sub.problem_id, []).append(sub)

        for problem in problems:
            self._problems_map[problem.id] = problem
            subs = self._submissions_map.get(problem.id, [])

            # Aggregate searchable document text
            notes_str = " ".join([n.content for n in problem.notes]) if hasattr(problem, "notes") and problem.notes else ""
            attempts_str = " ".join([f"{a.approach_summary} {a.reasoning or ''} {' '.join(a.mistakes)}" for a in problem.attempts]) if hasattr(problem, "attempts") and problem.attempts else ""

            text_parts = [
                problem.title,
                problem.statement or "",
                " ".join(problem.topics),
                problem.difficulty.value,
                notes_str,
                attempts_str,
            ]

            for sub in subs:
                text_parts.extend([
                    sub.code or "",
                    sub.status.value,
                ])

            full_text = " ".join(text_parts).lower()
            self._document_texts[problem.id] = full_text

            tokens = self._tokenize(full_text)
            unique_tokens = set(tokens)
            for token in unique_tokens:
                self._df[token] += 1

        self._num_docs = len(problems)

        # Compute TF-IDF vectors
        for problem_id, full_text in self._document_texts.items():
            tokens = self._tokenize(full_text)
            term_counts = Counter(tokens)
            total_terms = len(tokens) or 1

            vec: Dict[str, float] = {}
            for token, count in term_counts.items():
                tf = count / total_terms
                idf = math.log((1 + self._num_docs) / (1 + self._df[token])) + 1.0
                vec[token] = tf * idf

            # Normalize vector L2
            norm = math.sqrt(sum(val * val for val in vec.values())) or 1.0
            self._document_vectors[problem_id] = {k: v / norm for k, v in vec.items()}

    def search(self, query: str, top_k: int = 10) -> List[SemanticSearchResult]:
        """Perform semantic query matching using TF-IDF cosine similarity."""
        if not query.strip() or not self._num_docs:
            return []

        query_tokens = self._tokenize(query.lower())
        if not query_tokens:
            return []

        query_counts = Counter(query_tokens)
        total_q = len(query_tokens)

        # Query vector
        query_vec: Dict[str, float] = {}
        for token, count in query_counts.items():
            tf = count / total_q
            idf = math.log((1 + self._num_docs) / (1 + self._df.get(token, 0))) + 1.0
            query_vec[token] = tf * idf

        norm = math.sqrt(sum(v * v for v in query_vec.values())) or 1.0
        query_vec = {k: v / norm for k, v in query_vec.items()}

        scores: List[Tuple[str, float]] = []
        for problem_id, doc_vec in self._document_vectors.items():
            score = sum(query_vec[token] * doc_vec.get(token, 0.0) for token in query_vec)
            
            # Boost score for phrase/intent matches (e.g. "struggled", "sliding window")
            problem = self._problems_map[problem_id]
            subs = self._submissions_map.get(problem_id, [])
            has_fails = any(s.status.value in ("Wrong Answer", "Time Limit Exceeded", "Memory Limit Exceeded") for s in subs)

            if "struggl" in query.lower() or "failed" in query.lower():
                if has_fails or len(subs) > 2:
                    score *= 1.35
            if "optimize" in query.lower() or "hashmap" in query.lower():
                if "hashmap" in self._document_texts[problem_id] or "dict" in self._document_texts[problem_id]:
                    score *= 1.25

            if score > 0.01:
                scores.append((problem_id, score))

        scores.sort(key=lambda x: x[1], reverse=True)

        results: List[SemanticSearchResult] = []
        for problem_id, score in scores[:top_k]:
            problem = self._problems_map[problem_id]
            matched_snippet = self._extract_snippet(self._document_texts[problem_id], query_tokens)
            match_reason = f"TF-IDF similarity score: {score:.2f} matching concept terms"

            results.append(
                SemanticSearchResult(
                    problem=problem,
                    relevance_score=round(score, 3),
                    matched_snippet=matched_snippet,
                    match_reason=match_reason,
                )
            )

        return results

    def _tokenize(self, text: str) -> List[str]:
        """Normalize text into alphanumeric tokens."""
        return re.findall(r"\b[a-z0-9_]{2,}\b", text.lower())

    def _extract_snippet(self, text: str, query_tokens: List[str], max_len: int = 150) -> str:
        """Extract a representative snippet around matched query terms."""
        for token in query_tokens:
            pos = text.find(token)
            if pos != -1:
                start = max(0, pos - 30)
                end = min(len(text), pos + max_len)
                snippet = text[start:end].strip()
                return f"...{snippet}..." if start > 0 else f"{snippet}..."
        return text[:max_len] + "..." if len(text) > max_len else text
