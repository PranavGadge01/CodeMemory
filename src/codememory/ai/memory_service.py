"""Personal DSA Memory Service for grounded natural-language querying ("Ask CodeMemory")."""

from typing import Any, Dict, List, Optional
from codememory.ai.context_builder import ContextBuilder
from codememory.ai.providers.base_provider import BaseAIProvider
from codememory.ai.providers.heuristic_provider import HeuristicAIProvider
from codememory.domain.models import Problem


class MemoryService:
    """Combines problem history, submission history, AI analyses, and pattern statistics to answer grounded questions."""

    def __init__(
        self,
        storage: Any,
        search_service: Optional[Any] = None,
        ai_provider: Optional[BaseAIProvider] = None,
    ):
        self.storage = storage
        self.search_service = search_service
        self.ai_provider = ai_provider or HeuristicAIProvider()
        self.context_builder = ContextBuilder()

    def ask_codememory(self, question: str) -> Dict[str, Any]:
        """Process a natural language user query grounded strictly in stored CodeMemory records."""
        question_clean = (question or "").strip()
        if not question_clean:
            return {
                "question": question,
                "answer": "Please enter a question to query your CodeMemory database.",
                "sources": [],
                "context_used": "",
            }

        # 1. Retrieve relevant problems from storage/search
        all_problems: List[Problem] = list(self.storage.list_all())
        matching_problems: List[Problem] = []

        q_words = [w.lower() for w in question_clean.split() if len(w) > 2]
        for p in all_problems:
            title_match = any(w in p.title.lower() for w in q_words)
            topic_match = any(w in t.lower() for t in p.topics for w in q_words)
            stmt_match = bool(p.statement and any(w in p.statement.lower() for w in q_words))

            if title_match or topic_match or stmt_match:
                matching_problems.append(p)

        # Fallback to all problems if no specific keyword match
        selected_problems = matching_problems if matching_problems else all_problems[:10]

        # 2. Build grounded context
        context_str = self.context_builder.build_context(selected_problems, query=question_clean)

        # 3. Generate grounded answer
        answer = self.ai_provider.answer_question(question_clean, context_str)

        # 4. Formulate source citations
        sources = []
        for p in selected_problems:
            sources.append(
                {
                    "problem_id": p.id,
                    "title": p.title,
                    "difficulty": p.difficulty.value if hasattr(p.difficulty, "value") else str(p.difficulty),
                    "platform": p.platform.value if hasattr(p.platform, "value") else str(p.platform),
                    "topics": p.topics,
                    "attempts_count": len(p.attempts),
                }
            )

        return {
            "question": question_clean,
            "answer": answer,
            "sources": sources,
            "context_used": context_str,
        }
