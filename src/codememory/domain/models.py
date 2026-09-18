"""Pydantic domain models for CodeMemory."""

from datetime import datetime, timezone
import hashlib
import re
from typing import Any
import uuid

from pydantic import BaseModel, Field, field_validator

from codememory.domain.enums import DifficultyLevel, NoteType, Platform, SubmissionStatus


def generate_slug(title: str) -> str:
    """Generate a URL/folder-friendly slug from title."""
    s = str(title).lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return s.strip("-") or "problem"


def compute_submission_hash(
    problem_title: str,
    language: str,
    code: str,
    submitted_at: datetime | str | None,
    status: str,
) -> str:
    """Generate deterministic SHA256 hash for submission idempotency."""
    code_clean = (code or "").strip()
    lang_clean = (language or "").strip().lower()
    title_clean = generate_slug(problem_title or "")
    dt_str = str(submitted_at) if submitted_at else ""
    status_str = str(status).strip()

    raw = f"{title_clean}:{lang_clean}:{status_str}:{dt_str}:{code_clean}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class Topic(BaseModel):
    """DSA topic categorization."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    category: str | None = None
    description: str | None = None


class SolutionAnalysis(BaseModel):
    """Detailed technical analysis of a problem solution."""

    approach_name: str = "Standard Approach"
    time_complexity: str = "O(N)"
    space_complexity: str = "O(1)"
    key_insights: list[str] = Field(default_factory=list)
    trade_offs: str | None = None
    bottleneck: str | None = None


def _ensure_utc(v: Any) -> datetime:
    if isinstance(v, datetime):
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v
    if isinstance(v, str) and v.strip():
        try:
            dt = datetime.fromisoformat(v.strip().replace("Z", "+00:00"))
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            pass
    return datetime.now(timezone.utc)


class Submission(BaseModel):
    """Individual code submission record."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    problem_id: str
    attempt_id: str | None = None
    code: str
    language: str = "python"
    status: SubmissionStatus = SubmissionStatus.UNKNOWN
    runtime_ms: float | None = None
    memory_mb: float | None = None
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error_message: str | None = None
    submission_hash: str = ""

    @field_validator("submitted_at", mode="before")
    @classmethod
    def validate_submitted_at(cls, v: Any) -> datetime:
        return _ensure_utc(v)

    def model_post_init(self, __context: Any) -> None:
        """Compute submission hash if not provided."""
        if not self.submission_hash and self.code:
            self.submission_hash = compute_submission_hash(
                problem_title=self.problem_id,
                language=self.language,
                code=self.code,
                submitted_at=self.submitted_at,
                status=self.status.value,
            )


class Attempt(BaseModel):
    """Problem solving attempt containing zero or more code submissions."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    problem_id: str
    attempt_number: int = 1
    approach_summary: str = "Attempt"
    reasoning: str | None = None
    mistakes: list[str] = Field(default_factory=list)
    analysis: SolutionAnalysis | None = None
    status: SubmissionStatus = SubmissionStatus.UNKNOWN
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    submissions: list[Submission] = Field(default_factory=list)

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def validate_attempt_dates(cls, v: Any) -> datetime:
        return _ensure_utc(v)

    @property
    def latest_submission(self) -> Submission | None:
        """Get the most recent submission in this attempt."""
        if not self.submissions:
            return None
        return max(self.submissions, key=lambda s: _ensure_utc(s.submitted_at))

    @property
    def is_accepted(self) -> bool:
        """Check if any submission in this attempt was accepted."""
        return any(s.status == SubmissionStatus.ACCEPTED for s in self.submissions) or self.status == SubmissionStatus.ACCEPTED


class ProblemNote(BaseModel):
    """Human reasoning, intuition, or mistake note."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    problem_id: str
    attempt_id: str | None = None
    content: str
    note_type: NoteType = NoteType.GENERAL
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("created_at", mode="before")
    @classmethod
    def validate_note_date(cls, v: Any) -> datetime:
        return _ensure_utc(v)


class Problem(BaseModel):
    """Core domain model representing a DSA problem."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    slug: str = ""
    difficulty: DifficultyLevel = DifficultyLevel.UNKNOWN
    platform: Platform | str = Platform.LEETCODE
    url: str | None = None
    topics: list[str] = Field(default_factory=list)
    statement: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    attempts: list[Attempt] = Field(default_factory=list)
    notes: list[ProblemNote] = Field(default_factory=list)

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def validate_problem_dates(cls, v: Any) -> datetime:
        return _ensure_utc(v)

    @field_validator("slug", mode="before")
    @classmethod
    def set_slug_if_empty(cls, v: Any, info: Any) -> str:
        if v:
            return str(v)
        title = info.data.get("title", "") if hasattr(info, "data") and isinstance(info.data, dict) else ""
        return generate_slug(title)

    def model_post_init(self, __context: Any) -> None:
        """Ensure slug is set if missing after initialization."""
        if not self.slug and self.title:
            self.slug = generate_slug(self.title)

    @property
    def latest_accepted_attempt(self) -> Attempt | None:
        """Get latest attempt containing an accepted submission."""
        accepted = [a for a in self.attempts if a.is_accepted]
        if not accepted:
            return None
        return max(accepted, key=lambda a: a.updated_at)

    @property
    def latest_accepted_submission(self) -> Submission | None:
        """Get the latest accepted submission across all attempts."""
        accepted_subs: list[Submission] = []
        for attempt in self.attempts:
            for sub in attempt.submissions:
                if sub.status == SubmissionStatus.ACCEPTED:
                    accepted_subs.append(sub)
        if not accepted_subs:
            return None
        return max(accepted_subs, key=lambda s: s.submitted_at)

    @property
    def latest_submission(self) -> Submission | None:
        """Get the most recent submission regardless of status."""
        all_subs: list[Submission] = []
        for attempt in self.attempts:
            all_subs.extend(attempt.submissions)
        if not all_subs:
            return None
        return max(all_subs, key=lambda s: s.submitted_at)
