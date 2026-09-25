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


def _parse_any_timestamp(value: Any) -> datetime | None:
    """Best-effort parse of any timestamp representation into a UTC datetime.

    Returns ``None`` when the value cannot be interpreted as a timestamp.
    """
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        val = float(value)
        if val > 1e11:  # epoch milliseconds
            val /= 1000.0
        return datetime.fromtimestamp(val, tz=timezone.utc)

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        # Numeric strings are epoch seconds or epoch milliseconds.
        try:
            val = float(text)
        except ValueError:
            val = None
        if val is not None:
            if val > 1e11:
                val /= 1000.0
            return datetime.fromtimestamp(val, tz=timezone.utc)

        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
            return dt
        except ValueError:
            return None

    return None


def canonical_timestamp(value: Any) -> str:
    """Render any timestamp representation as one stable UTC ISO string.

    This is the single serialization used for submission hashing. Normalizing
    here means a tz-aware datetime, a naive-but-UTC datetime, an epoch number,
    and an epoch string all produce the *same* fingerprint, which is what makes
    deduplication work across the import and sync entry points.
    """
    if value is None:
        return ""
    dt = _parse_any_timestamp(value)
    if dt is None:
        return str(value).strip()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def compute_submission_hash(
    problem_title: str,
    language: str,
    code: str,
    submitted_at: datetime | str | None,
    status: str,
    source_account: str | None = None,
) -> str:
    """Generate the canonical deterministic SHA256 hash for a submission.

    This is the ONE submission identity hash in CodeMemory. Every entry point
    (file import, connector normalization, live sync) must funnel through here.

    When ``source_account`` provenance is available it is folded into the hash
    so that equivalent submissions from different accounts produce distinct
    hashes and therefore do not cross-deduplicate. Legacy submissions without
    an ``source_account`` keep their original hash (backward compatible).
    """
    code_clean = (code or "").strip()
    lang_clean = (language or "").strip().lower()
    title_clean = generate_slug(problem_title or "")
    dt_str = canonical_timestamp(submitted_at)
    status_str = str(status).strip()

    if source_account is not None:
        account_clean = str(source_account).strip()
        raw = f"{account_clean}:{title_clean}:{lang_clean}:{status_str}:{dt_str}:{code_clean}"
    else:
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
    source_provider: str | None = None
    source_account: str | None = None

    @field_validator("submitted_at", mode="before")
    @classmethod
    def validate_submitted_at(cls, v: Any) -> datetime:
        return _ensure_utc(v)

    def model_post_init(self, __context: Any) -> None:
        """Compute the canonical submission hash when the caller did not supply one.

        The hash is intentionally NOT gated on ``code``: a submission without
        source code is still a real submission, and hashing it is what prevents
        code-less records from collapsing into a single stored row.

        Provenance (``source_account``) is included in the hash when present so
        that equivalent submissions from different accounts get distinct hashes.
        """
        if not self.submission_hash:
            self.submission_hash = compute_submission_hash(
                problem_title=self.problem_id,
                language=self.language,
                code=self.code,
                submitted_at=self.submitted_at,
                status=self.status.value,
                source_account=self.source_account,
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

    def _get_source_provider(self) -> str | None:
        """Return source_provider of the first non-null submission in this attempt."""
        for sub in self.submissions:
            if sub.source_provider is not None:
                return sub.source_provider
        return None

    def _get_source_account(self) -> str | None:
        """Return source_account of the first non-null submission in this attempt."""
        for sub in self.submissions:
            if sub.source_account is not None:
                return sub.source_account
        return None


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

    def _get_source_provider(self) -> str | None:
        """Return the source_provider of the first non-null submission, or None.

        A problem may have submissions from multiple providers (e.g. LeetCode
        and manually imported). For memory-provenance purposes we use the first
        non-null value encountered; if all submissions are manual (None), the
        problem is considered non-provider-sourced.
        """
        for attempt in self.attempts:
            for sub in attempt.submissions:
                if sub.source_provider is not None:
                    return sub.source_provider
        return None

    def _get_source_account(self) -> str | None:
        """Return the source_account of the first non-null submission, or None.

        Mirrors ``_get_source_provider`` for account provenance.
        """
        for attempt in self.attempts:
            for sub in attempt.submissions:
                if sub.source_account is not None:
                    return sub.source_account
        return None
