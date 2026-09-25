"""LeetCode mapper converting raw LeetCode structures into CodeMemory normalized schemas."""

from typing import Any, List, Optional

from codememory.connectors.leetcode.models import LeetCodeSubmissionRaw
from codememory.domain.enums import DifficultyLevel, SubmissionStatus
from codememory.domain.import_schema import NormalizedSubmissionRecord, normalize_language
from codememory.domain.models import generate_slug


STATUS_MAP: dict[str, SubmissionStatus] = {
    "accepted": SubmissionStatus.ACCEPTED,
    "ac": SubmissionStatus.ACCEPTED,
    "10": SubmissionStatus.ACCEPTED,
    "wrong answer": SubmissionStatus.WRONG_ANSWER,
    "wa": SubmissionStatus.WRONG_ANSWER,
    "11": SubmissionStatus.WRONG_ANSWER,
    "time limit exceeded": SubmissionStatus.TIME_LIMIT_EXCEEDED,
    "tle": SubmissionStatus.TIME_LIMIT_EXCEEDED,
    "12": SubmissionStatus.TIME_LIMIT_EXCEEDED,
    "memory limit exceeded": SubmissionStatus.MEMORY_LIMIT_EXCEEDED,
    "mle": SubmissionStatus.MEMORY_LIMIT_EXCEEDED,
    "13": SubmissionStatus.MEMORY_LIMIT_EXCEEDED,
    "runtime error": SubmissionStatus.RUNTIME_ERROR,
    "re": SubmissionStatus.RUNTIME_ERROR,
    "14": SubmissionStatus.RUNTIME_ERROR,
    "compile error": SubmissionStatus.COMPILE_ERROR,
    "ce": SubmissionStatus.COMPILE_ERROR,
    "15": SubmissionStatus.COMPILE_ERROR,
}

class LeetCodeMapper:
    """Mapper translating raw LeetCode data to normalized CodeMemory schema."""

    @staticmethod
    def normalize_status(raw_status: str) -> SubmissionStatus:
        """Map raw status string to standard SubmissionStatus enum."""
        if not raw_status:
            return SubmissionStatus.UNKNOWN
        clean = raw_status.strip().lower()
        return STATUS_MAP.get(clean, SubmissionStatus.UNKNOWN)

    @staticmethod
    def normalize_language(raw_lang: str) -> str:
        """Standardize programming language names via the canonical vocabulary."""
        return normalize_language(raw_lang)

    @staticmethod
    def normalize_difficulty(raw_diff: Optional[str]) -> str:
        """Standardize difficulty string, defaulting to Unknown when absent/unrecognized."""
        if not raw_diff:
            return DifficultyLevel.UNKNOWN.value
        clean = raw_diff.strip().capitalize()
        if clean in {d.value for d in DifficultyLevel}:
            return clean
        return DifficultyLevel.UNKNOWN.value

    @classmethod
    def to_normalized_problem(cls, raw_prob: "LeetCodeProblemRaw") -> dict:
        """Map raw LeetCode problem data into a normalized problem dict for service.add_problem()."""
        from codememory.connectors.leetcode.models import LeetCodeProblemRaw as _ProbRaw
        slug = raw_prob.title_slug or generate_slug(raw_prob.title)
        return {
            "title": raw_prob.title,
            "slug": slug,
            "difficulty": cls.normalize_difficulty(raw_prob.difficulty),
            "topics": raw_prob.topics or [],
            "url": raw_prob.url or f"https://leetcode.com/problems/{slug}/",
            "statement": raw_prob.content,
        }

    @classmethod
    def to_normalized_record(
        cls, raw: LeetCodeSubmissionRaw, source_account: str | None = None
    ) -> NormalizedSubmissionRecord:
        """Map a raw LeetCode submission into the canonical CodeMemory record.

        Deliberately thin: timestamp parsing, runtime/memory parsing and hash
        computation all happen inside ``NormalizedSubmissionRecord`` so that every
        entry point converges on one normalized representation. Only the
        LeetCode-specific vocabulary mappings (numeric status codes, language
        identifiers) are applied here, in the transport layer where they belong.

        ``source_account`` is passed in so it is available during the record's
        ``model_post_init`` hash computation — provenance must be assigned BEFORE
        the hash is derived so cross-account submissions get distinct hashes.
        """
        slug = raw.title_slug or generate_slug(raw.title)

        sub_id = raw.submission_id or raw.id
        external_id = f"leetcode_{sub_id}" if sub_id else None

        url = raw.url
        if not url and slug:
            url = f"https://leetcode.com/problems/{slug}/"

        return NormalizedSubmissionRecord(
            problem_id=slug,
            title=raw.title,
            difficulty=cls.normalize_difficulty(raw.difficulty),
            topics=raw.topics,
            url=url,
            language=cls.normalize_language(raw.language),
            code=raw.code,
            timestamp=raw.timestamp,
            status=cls.normalize_status(raw.status),
            runtime=raw.runtime,
            memory=raw.memory,
            reasoning=raw.reasoning or raw.notes,
            submission_id=external_id,
            source_provider="leetcode",
            source_account=source_account,
        )
