"""Abstract base repository interfaces for CodeMemory storage abstraction layer."""

from abc import ABC, abstractmethod
from typing import Sequence

from codememory.domain.models import Attempt, Problem, Submission


class ProblemRepository(ABC):
    """Abstract interface for Problem persistence operations."""

    @abstractmethod
    def save(self, problem: Problem) -> Problem:
        """Save or update a problem."""
        pass

    @abstractmethod
    def get_by_id(self, problem_id: str) -> Problem | None:
        """Find problem by ID."""
        pass

    @abstractmethod
    def get_by_slug(self, slug: str) -> Problem | None:
        """Find problem by slug."""
        pass

    @abstractmethod
    def list_all(self) -> Sequence[Problem]:
        """Retrieve all problems."""
        pass

    @abstractmethod
    def delete(self, problem_id: str) -> bool:
        """Delete problem by ID."""
        pass


class SubmissionRepository(ABC):
    """Abstract interface for Submission persistence operations."""

    @abstractmethod
    def save(self, submission: Submission) -> Submission:
        """Save or update a submission."""
        pass

    @abstractmethod
    def get_by_id(self, submission_id: str) -> Submission | None:
        """Find submission by ID."""
        pass

    @abstractmethod
    def get_by_hash(self, submission_hash: str) -> Submission | None:
        """Find submission by deterministic hash."""
        pass

    @abstractmethod
    def list_by_problem(self, problem_id: str) -> Sequence[Submission]:
        """Find all submissions for a problem."""
        pass

    @abstractmethod
    def list_by_attempt(self, attempt_id: str) -> Sequence[Submission]:
        """Find all submissions for a specific attempt."""
        pass


class AttemptRepository(ABC):
    """Abstract interface for Attempt persistence operations."""

    @abstractmethod
    def save(self, attempt: Attempt) -> Attempt:
        """Save or update an attempt."""
        pass

    @abstractmethod
    def get_by_id(self, attempt_id: str) -> Attempt | None:
        """Find attempt by ID."""
        pass

    @abstractmethod
    def list_by_problem(self, problem_id: str) -> Sequence[Attempt]:
        """Find all attempts for a problem ordered chronologically."""
        pass
