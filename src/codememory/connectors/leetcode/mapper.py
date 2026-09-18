"""LeetCode mapper converting raw LeetCode structures into CodeMemory normalized schemas."""

from datetime import datetime, timezone
import hashlib
from typing import Any, List, Optional

from codememory.connectors.leetcode.models import LeetCodeSubmissionRaw
from codememory.domain.enums import DifficultyLevel, SubmissionStatus
from codememory.domain.import_schema import NormalizedSubmissionRecord
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

LANGUAGE_MAP: dict[str, str] = {
    "python3": "Python",
    "python": "Python",
    "py3": "Python",
    "py": "Python",
    "cpp": "C++",
    "c++": "C++",
    "cplusplus": "C++",
    "java": "Java",
    "golang": "Go",
    "go": "Go",
    "javascript": "JavaScript",
    "js": "JavaScript",
    "typescript": "TypeScript",
    "ts": "TypeScript",
    "rust": "Rust",
    "rs": "Rust",
    "c": "C",
    "csharp": "C#",
    "c#": "C#",
    "kotlin": "Kotlin",
    "kt": "Kotlin",
    "swift": "Swift",
    "ruby": "Ruby",
    "rb": "Ruby",
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
        """Standardize programming language names."""
        if not raw_lang:
            return "Unknown"
        clean = raw_lang.strip().lower()
        return LANGUAGE_MAP.get(clean, raw_lang.strip().capitalize())

    @staticmethod
    def normalize_difficulty(raw_diff: Optional[str]) -> str:
        """Standardize difficulty string."""
        if not raw_diff:
            return DifficultyLevel.MEDIUM.value
        clean = raw_diff.strip().capitalize()
        if clean in {d.value for d in DifficultyLevel}:
            return clean
        return DifficultyLevel.MEDIUM.value

    @staticmethod
    def parse_timestamp(raw_ts: Any) -> str:
        """Parse epoch seconds/milliseconds, int, float, or string to ISO 8601 UTC string."""
        if raw_ts is None:
            return datetime.now(timezone.utc).isoformat()

        try:
            if isinstance(raw_ts, (int, float)):
                val = float(raw_ts)
                # Handle milliseconds timestamp
                if val > 1e11:
                    val /= 1000.0
                return datetime.fromtimestamp(val, tz=timezone.utc).isoformat()
            
            ts_str = str(raw_ts).strip()
            # Numeric string
            if ts_str.replace(".", "", 1).isdigit():
                val = float(ts_str)
                if val > 1e11:
                    val /= 1000.0
                return datetime.fromtimestamp(val, tz=timezone.utc).isoformat()
            
            # ISO format string
            dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except Exception:
            return datetime.now(timezone.utc).isoformat()

    @classmethod
    def compute_submission_hash(
        cls,
        problem_slug: str,
        timestamp_str: str,
        language: str,
        status: SubmissionStatus,
        code: str,
    ) -> str:
        """Generate deterministic SHA-256 submission hash for deduplication."""
        fingerprint = f"{problem_slug}:{timestamp_str}:{language}:{status.value}:{code.strip()}"
        return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()

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
    def to_normalized_record(cls, raw: LeetCodeSubmissionRaw) -> NormalizedSubmissionRecord:
        """Map raw LeetCode submission model into CodeMemory NormalizedSubmissionRecord."""
        slug = raw.title_slug or generate_slug(raw.title)
        norm_status = cls.normalize_status(raw.status)
        norm_lang = cls.normalize_language(raw.language)
        norm_diff = cls.normalize_difficulty(raw.difficulty)
        norm_ts = cls.parse_timestamp(raw.timestamp)

        sub_id = raw.submission_id or raw.id
        external_id = f"leetcode_{sub_id}" if sub_id else None

        url = raw.url
        if not url and slug:
            url = f"https://leetcode.com/problems/{slug}/"

        computed_hash = cls.compute_submission_hash(
            problem_slug=slug,
            timestamp_str=norm_ts,
            language=norm_lang,
            status=norm_status,
            code=raw.code,
        )

        return NormalizedSubmissionRecord(
            title=raw.title,
            difficulty=norm_diff,
            topics=raw.topics,
            url=url,
            language=norm_lang,
            code=raw.code,
            timestamp=norm_ts,
            status=norm_status,
            runtime=raw.runtime,
            memory=raw.memory,
            reasoning=raw.reasoning or raw.notes,
            submission_id=external_id,
            submission_hash=computed_hash,
        )
