"""ContextBuilder for constructing bounded, grounded context for AI queries."""

from typing import List, Optional
from codememory.domain.models import Problem, Submission, Attempt
from codememory.ai.models import SubmissionAnalysis


class ContextBuilder:
    """Retrieves and formats concise, bounded historical context for grounded AI queries."""

    def __init__(self, max_context_chars: int = 4000):
        self.max_context_chars = max_context_chars

    def build_context(
        self,
        problems: List[Problem],
        query: str = "",
        ai_analyses: Optional[List[SubmissionAnalysis]] = None,
    ) -> str:
        """Format bounded context text from problem history and submission attempts."""
        if not problems:
            return "No relevant problem records found in CodeMemory."

        context_blocks: List[str] = []

        for p in problems[:10]:
            diff_str = p.difficulty.value if hasattr(p.difficulty, "value") else str(p.difficulty)
            plat_str = p.platform.value if hasattr(p.platform, "value") else str(p.platform)
            topics_str = ", ".join(p.topics) if p.topics else "None"

            block_lines = [
                f"--- Problem: {p.title} (ID: {p.id}) ---",
                f"Platform: {plat_str} | Difficulty: {diff_str} | Topics: {topics_str}",
            ]

            if p.attempts:
                block_lines.append(f"Recorded Attempts: {len(p.attempts)}")
                for att in sorted(p.attempts, key=lambda a: a.attempt_number):
                    status_str = att.status.value if hasattr(att.status, "value") else str(att.status)
                    summary = att.approach_summary or "Standard Approach"
                    block_lines.append(f"  Attempt {att.attempt_number}: Status={status_str}, Approach={summary}")
                    if att.reasoning:
                        block_lines.append(f"    Reasoning: {att.reasoning[:150]}")

                    for sub in att.submissions[:2]:
                        sub_status = sub.status.value if hasattr(sub.status, "value") else str(sub.status)
                        code_snippet = (sub.code or "")[:200].replace("\n", " ")
                        block_lines.append(f"    Sub ({sub.language}, {sub_status}): {code_snippet}...")

            context_blocks.append("\n".join(block_lines))

        full_context = "\n\n".join(context_blocks)
        if len(full_context) > self.max_context_chars:
            full_context = full_context[: self.max_context_chars] + "\n...[Context Truncated for Size]"

        return full_context
