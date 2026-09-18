"""Domain model exports for CodeMemory."""

from codememory.domain.enums import DifficultyLevel, NoteType, Platform, SubmissionStatus
from codememory.domain.exceptions import (
    AttemptNotFoundError,
    CodeMemoryError,
    DuplicateSubmissionError,
    ImportError,
    ProblemNotFoundError,
    StorageError,
    SubmissionNotFoundError,
    ValidationError,
)
from codememory.domain.import_schema import NormalizedSubmissionRecord
from codememory.domain.models import (
    Attempt,
    Problem,
    ProblemNote,
    SolutionAnalysis,
    Submission,
    Topic,
    compute_submission_hash,
    generate_slug,
)

__all__ = [
    "SubmissionStatus",
    "DifficultyLevel",
    "Platform",
    "NoteType",
    "CodeMemoryError",
    "ProblemNotFoundError",
    "SubmissionNotFoundError",
    "AttemptNotFoundError",
    "DuplicateSubmissionError",
    "ValidationError",
    "StorageError",
    "ImportError",
    "Topic",
    "SolutionAnalysis",
    "Submission",
    "Attempt",
    "ProblemNote",
    "Problem",
    "NormalizedSubmissionRecord",
    "generate_slug",
    "compute_submission_hash",
]
