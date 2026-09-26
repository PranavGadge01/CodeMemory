"""Normalized import schema for CodeMemory data ingestion."""

from datetime import datetime, timezone
import re
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from codememory.domain.enums import DifficultyLevel, SubmissionStatus
from codememory.domain.models import compute_submission_hash, generate_slug

def parse_runtime(value: Any) -> float | None:
    """Parse runtime input into float milliseconds."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)

    s = str(value).strip().lower()
    match = re.search(r"([\d.]+)\s*(ms|s|sec|seconds)?", s)
    if match:
        val = float(match.group(1))
        unit = match.group(2)
        if unit in ("s", "sec", "seconds"):
            return val * 1000.0
        return val
    return None


def parse_memory(value: Any) -> float | None:
    """Parse memory input into float megabytes."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)

    s = str(value).strip().lower()
    match = re.search(r"([\d.]+)\s*(mb|kb|gb|b|bytes|megabytes)?", s)
    if match:
        val = float(match.group(1))
        unit = match.group(2)
        if unit == "kb":
            return val / 1024.0
        if unit == "gb":
            return val * 1024.0
        if unit in ("b", "bytes"):
            return val / (1024.0 * 1024.0)
        return val
    return None


def parse_timestamp(value: Any) -> datetime:
    """Parse datetime from ISO string, epoch timestamp, or format variants."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, (int, float)):
        # Epoch seconds or milliseconds
        val_sec = float(value)
        if val_sec > 1e11:  # milliseconds
            val_sec /= 1000.0
        return datetime.fromtimestamp(val_sec, tz=timezone.utc)
    if isinstance(value, str) and value.strip():
        val_str = value.strip()

        # Numeric strings are epoch seconds or milliseconds.
        # Without this branch, "1700000000" falls through to the format table
        # below, matches nothing, and silently becomes "now".
        try:
            val_sec = float(val_str)
        except ValueError:
            val_sec = None
        if val_sec is not None:
            if val_sec > 1e11:
                val_sec /= 1000.0
            return datetime.fromtimestamp(val_sec, tz=timezone.utc)

        # ISO format standard parsing
        try:
            dt = datetime.fromisoformat(val_str.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            pass

        # Try common date formats
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d",
            "%m/%d/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
            "%b %d, %Y",
        ):
            try:
                dt = datetime.strptime(val_str, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue

    return datetime.now(timezone.utc)


def parse_topics(value: Any) -> list[str]:
    """Parse topic list from list or comma-separated string."""
    if not value:
        return []
    if isinstance(value, list):
        return [str(t).strip() for t in value if str(t).strip()]
    if isinstance(value, str):
        return [t.strip() for t in value.split(",") if t.strip()]
    return []


# One canonical language vocabulary. Platform-specific spellings ("python3",
# "golang", "cpp") are mapped to CodeMemory's internal names; anything unknown
# passes through unchanged rather than being falsely "corrected".
LANGUAGE_ALIASES: dict[str, str] = {
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


def normalize_language(value: Any) -> str:
    """Canonicalize a programming language identifier.

    This is the ONE place language spelling is normalized, so the file-import,
    connector and sync entry points cannot disagree on a submission's language —
    which would otherwise produce different deduplication hashes for the same
    submission.
    """
    if value is None:
        return "Unknown"
    text = str(value).strip()
    if not text:
        return "Unknown"
    return LANGUAGE_ALIASES.get(text.lower(), text)

class NormalizedSubmissionRecord(BaseModel):
    """Normalized import schema accepting diverse JSON/CSV/JSONL input shapes."""

    problem_id: str | None = None
    submission_id: str | None = None
    title: str
    difficulty: DifficultyLevel = DifficultyLevel.UNKNOWN
    topics: list[str] = Field(default_factory=list)
    url: str | None = None
    language: str = "python"
    code: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: SubmissionStatus = SubmissionStatus.UNKNOWN
    runtime_ms: float | None = None
    memory_mb: float | None = None
    statement: str | None = None
    reasoning: str | None = None
    submission_hash: str = ""
    source_provider: str | None = None
    source_account: str | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_input_keys(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        d = dict(data)
        # title aliases
        if "title" not in d or not d["title"]:
            for alt in ("problem_title", "problem_name", "name", "problem"):
                if alt in d and d[alt]:
                    d["title"] = d[alt]
                    break

        # Problem identity: prefer the platform's authoritative slug when present
        # (LeetCode's titleSlug), since a slug derived from the title can diverge
        # from the real one.
        if "problem_id" not in d or not d["problem_id"]:
            for alt in ("title_slug", "problem_slug", "slug"):
                if alt in d and d[alt]:
                    d["problem_id"] = d[alt]
                    break

        # runtime aliases
        if "runtime_ms" not in d or d["runtime_ms"] is None:
            for alt in ("runtime", "time_ms", "execution_time", "time_taken"):
                if alt in d and d[alt] is not None:
                    d["runtime_ms"] = d[alt]
                    break

        # memory aliases
        if "memory_mb" not in d or d["memory_mb"] is None:
            for alt in ("memory", "memory_used", "space_mb"):
                if alt in d and d[alt] is not None:
                    d["memory_mb"] = d[alt]
                    break

        # timestamp aliases
        if "timestamp" not in d or not d["timestamp"]:
            for alt in ("submitted_at", "date", "time", "created_at"):
                if alt in d and d[alt]:
                    d["timestamp"] = d[alt]
                    break

        # topics aliases
        if "topics" not in d or not d["topics"]:
            for alt in ("tags", "category", "categories"):
                if alt in d and d[alt]:
                    d["topics"] = d[alt]
                    break

        # statement aliases
        if "statement" not in d or not d["statement"]:
            for alt in ("problem_statement", "description", "content"):
                if alt in d and d[alt]:
                    d["statement"] = d[alt]
                    break

        return d

    @field_validator("title", mode="before")
    @classmethod
    def validate_title(cls, v: Any) -> str:
        if not v or not str(v).strip():
            return "Untitled Problem"
        return str(v).strip()

    @field_validator("difficulty", mode="before")
    @classmethod
    def validate_difficulty(cls, v: Any) -> DifficultyLevel:
        return DifficultyLevel.parse(v)

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v: Any) -> SubmissionStatus:
        return SubmissionStatus.parse(v)

    @field_validator("topics", mode="before")
    @classmethod
    def validate_topics(cls, v: Any) -> list[str]:
        return parse_topics(v)

    @field_validator("language", mode="before")
    @classmethod
    def validate_language(cls, v: Any) -> str:
        return normalize_language(v)

    @field_validator("runtime_ms", mode="before")
    @classmethod
    def validate_runtime(cls, v: Any) -> float | None:
        return parse_runtime(v)

    @field_validator("memory_mb", mode="before")
    @classmethod
    def validate_memory(cls, v: Any) -> float | None:
        return parse_memory(v)

    @field_validator("timestamp", mode="before")
    @classmethod
    def validate_timestamp(cls, v: Any) -> datetime:
        return parse_timestamp(v)

    @field_validator("code", mode="before")
    @classmethod
    def validate_code(cls, v: Any) -> str:
        return str(v) if v is not None else ""

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization slug, ID, and hash normalization."""
        if not self.problem_id and self.title:
            self.problem_id = generate_slug(self.title)

        # Always derive a hash, including for code-less records. Gate only on
        # the caller having supplied one, never on the presence of code.
        if not self.submission_hash:
            self.submission_hash = compute_submission_hash(
                problem_title=self.problem_id or self.title,
                language=self.language,
                code=self.code,
                submitted_at=self.timestamp,
                status=self.status.value,
                source_account=self.source_account,
            )
