"""Pipeline to convert CodeMemory records into unified MemoryDocuments."""

from typing import List, Sequence
from codememory.ai.analyzer import AICodeAnalyzer
from codememory.domain.enums import SubmissionStatus
from codememory.domain.models import Problem
from codememory.memory.models import MemoryDocument, MemoryType, compute_content_hash


class DocumentPipeline:
    """Extracts searchable MemoryDocument items from raw domain problems & submission history."""

    def __init__(self, ai_analyzer: AICodeAnalyzer | None = None):
        self.ai_analyzer = ai_analyzer

    def extract_documents(self, problems: Sequence[Problem]) -> List[MemoryDocument]:
        """Convert a sequence of domain problems into detailed memory documents."""
        docs: List[MemoryDocument] = []

        for p in problems:
            diff_str = p.difficulty.value if hasattr(p.difficulty, "value") else str(p.difficulty)
            plat_str = p.platform.value if hasattr(p.platform, "value") else str(p.platform)

            # 1. Problem Metadata Document
            prob_content = (
                f"Problem: {p.title}\n"
                f"Difficulty: {diff_str}\n"
                f"Topics: {', '.join(p.topics) if p.topics else 'None'}\n"
                f"Statement: {p.statement or 'Not specified'}"
            )
            docs.append(
                MemoryDocument(
                    memory_id=f"prob_{p.id}",
                    memory_type=MemoryType.PROBLEM,
                    problem_id=p.id,
                    title=p.title,
                    content=prob_content,
                    topics=p.topics,
                    difficulty=diff_str,
                    platform=plat_str,
                    status="Solved" if p.latest_accepted_submission else "In Progress",
                    timestamp=p.created_at,
                    source="Problem Metadata",
                    source_reference={"problem_id": p.id, "slug": p.slug},
                    content_hash=compute_content_hash(prob_content),
                )
            )

            # 2. Process Attempts and Submissions
            for att in p.attempts:
                att_status_str = att.status.value if hasattr(att.status, "value") else str(att.status)
                att_content = (
                    f"Attempt #{att.attempt_number} for '{p.title}'\n"
                    f"Status: {att_status_str}\n"
                    f"Approach: {att.approach_summary or 'Standard Approach'}\n"
                    f"Reasoning: {att.reasoning or 'None'}"
                )

                docs.append(
                    MemoryDocument(
                        memory_id=f"att_{att.id}",
                        memory_type=MemoryType.ATTEMPT,
                        problem_id=p.id,
                        title=f"{p.title} - Attempt #{att.attempt_number}",
                        content=att_content,
                        topics=p.topics,
                        difficulty=diff_str,
                        platform=plat_str,
                        status=att_status_str,
                        attempt_number=att.attempt_number,
                        timestamp=att.created_at,
                        source="Attempt Reasoning",
                        source_reference={"problem_id": p.id, "attempt_id": att.id, "attempt_number": att.attempt_number},
                        content_hash=compute_content_hash(att_content),
                    )
                )

                # Record mistakes if present
                if att.mistakes or not att.is_accepted:
                    mistake_text = (
                        f"Mistake in '{p.title}' Attempt #{att.attempt_number} ({att_status_str}):\n"
                        f"{', '.join(att.mistakes) if att.mistakes else 'Failed attempt check.'}"
                    )
                    docs.append(
                        MemoryDocument(
                            memory_id=f"mistake_{att.id}",
                            memory_type=MemoryType.MISTAKE,
                            problem_id=p.id,
                            title=f"{p.title} - Mistake in Attempt #{att.attempt_number}",
                            content=mistake_text,
                            topics=p.topics,
                            difficulty=diff_str,
                            platform=plat_str,
                            status=att_status_str,
                            attempt_number=att.attempt_number,
                            timestamp=att.created_at,
                            source="Attempt Failure / Mistake Log",
                            source_reference={"problem_id": p.id, "attempt_id": att.id},
                            content_hash=compute_content_hash(mistake_text),
                        )
                    )

                # Process Submissions
                for sub in att.submissions:
                    sub_status_str = sub.status.value if hasattr(sub.status, "value") else str(sub.status)
                    sub_content = (
                        f"Submission for '{p.title}' ({sub.language}, {sub_status_str})\n"
                        f"Runtime: {sub.runtime_ms or 'N/A'} ms | Memory: {sub.memory_mb or 'N/A'} MB\n"
                        f"Code:\n```\n{(sub.code or '').strip()}\n```"
                    )

                    docs.append(
                        MemoryDocument(
                            memory_id=f"sub_{sub.id}",
                            memory_type=MemoryType.SUBMISSION,
                            problem_id=p.id,
                            submission_id=sub.id,
                            attempt_number=att.attempt_number,
                            title=f"{p.title} - {sub.language} Code Submission",
                            content=sub_content,
                            topics=p.topics,
                            difficulty=diff_str,
                            platform=plat_str,
                            status=sub_status_str,
                            language=sub.language,
                            timestamp=sub.submitted_at,
                            source="Raw Submission Code",
                            source_reference={"problem_id": p.id, "attempt_id": att.id, "submission_id": sub.id},
                            content_hash=compute_content_hash(sub_content),
                        )
                    )

                    # Extract AI Analysis document if analyzer available
                    if self.ai_analyzer:
                        try:
                            ai_res = self.ai_analyzer.analyze_submission(sub, p)
                            ai_content = (
                                f"AI Analysis for '{p.title}' ({sub_status_str}):\n"
                                f"Approach: {ai_res.approach}\n"
                                f"Algorithms: {', '.join(ai_res.algorithms)}\n"
                                f"Data Structures: {', '.join(ai_res.data_structures)}\n"
                                f"Pattern: {ai_res.inferred_pattern}\n"
                                f"Complexities: Time {ai_res.time_complexity}, Space {ai_res.space_complexity}\n"
                                f"Certain Facts: {', '.join(ai_res.certain_facts)}\n"
                                f"Likely Explanations: {', '.join(ai_res.likely_explanations)}"
                            )
                            docs.append(
                                MemoryDocument(
                                    memory_id=f"ai_{sub.id}",
                                    memory_type=MemoryType.AI_ANALYSIS,
                                    problem_id=p.id,
                                    submission_id=sub.id,
                                    title=f"{p.title} - AI Code Analysis",
                                    content=ai_content,
                                    topics=p.topics,
                                    patterns=[ai_res.inferred_pattern],
                                    difficulty=diff_str,
                                    platform=plat_str,
                                    status=sub_status_str,
                                    language=sub.language,
                                    timestamp=sub.submitted_at,
                                    source="AI Analysis Engine",
                                    source_reference={"problem_id": p.id, "submission_id": sub.id},
                                    content_hash=compute_content_hash(ai_content),
                                )
                            )
                        except Exception:
                            pass

        return docs
