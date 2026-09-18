"""Domain and storage exception classes for CodeMemory."""


class CodeMemoryError(Exception):
    """Base exception for all CodeMemory errors."""

    pass


class ProblemNotFoundError(CodeMemoryError):
    """Raised when a requested problem is not found."""

    def __init__(self, identifier: str):
        self.identifier = identifier
        super().__init__(f"Problem not found: '{identifier}'")


class SubmissionNotFoundError(CodeMemoryError):
    """Raised when a submission is not found."""

    def __init__(self, submission_id: str):
        self.submission_id = submission_id
        super().__init__(f"Submission not found: '{submission_id}'")


class AttemptNotFoundError(CodeMemoryError):
    """Raised when an attempt is not found."""

    def __init__(self, attempt_id: str):
        self.attempt_id = attempt_id
        super().__init__(f"Attempt not found: '{attempt_id}'")


class DuplicateSubmissionError(CodeMemoryError):
    """Raised when attempting to insert a duplicate submission."""

    def __init__(self, submission_id: str):
        self.submission_id = submission_id
        super().__init__(f"Duplicate submission detected: '{submission_id}'")


class ValidationError(CodeMemoryError):
    """Raised when domain or import data validation fails."""

    pass


class StorageError(CodeMemoryError):
    """Raised when storage operations fail."""

    pass


class ImportError(CodeMemoryError):
    """Raised when data ingestion/import fails."""

    pass
