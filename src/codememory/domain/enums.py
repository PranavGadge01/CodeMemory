"""Domain enumeration types for CodeMemory."""

from enum import Enum
from typing import Any


class SubmissionStatus(str, Enum):
    """Execution status of a code submission."""

    ACCEPTED = "Accepted"
    WRONG_ANSWER = "Wrong Answer"
    TIME_LIMIT_EXCEEDED = "Time Limit Exceeded"
    MEMORY_LIMIT_EXCEEDED = "Memory Limit Exceeded"
    RUNTIME_ERROR = "Runtime Error"
    COMPILE_ERROR = "Compile Error"
    UNKNOWN = "Unknown"

    @classmethod
    def parse(cls, value: Any) -> "SubmissionStatus":
        """Parse status string safely with normalization."""
        if not value:
            return cls.UNKNOWN
        if isinstance(value, cls):
            return value

        val_norm = getattr(value, "value", str(value)).strip().lower().replace("_", " ").replace("-", " ")
        mapping = {
            "accepted": cls.ACCEPTED,
            "ac": cls.ACCEPTED,
            "wrong answer": cls.WRONG_ANSWER,
            "wa": cls.WRONG_ANSWER,
            "time limit exceeded": cls.TIME_LIMIT_EXCEEDED,
            "tle": cls.TIME_LIMIT_EXCEEDED,
            "memory limit exceeded": cls.MEMORY_LIMIT_EXCEEDED,
            "mle": cls.MEMORY_LIMIT_EXCEEDED,
            "runtime error": cls.RUNTIME_ERROR,
            "re": cls.RUNTIME_ERROR,
            "compile error": cls.COMPILE_ERROR,
            "ce": cls.COMPILE_ERROR,
            "compilation error": cls.COMPILE_ERROR,
        }
        return mapping.get(val_norm, cls.UNKNOWN)


class DifficultyLevel(str, Enum):
    """Problem difficulty levels."""

    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"
    UNKNOWN = "Unknown"

    @classmethod
    def parse(cls, value: Any) -> "DifficultyLevel":
        """Parse difficulty string safely."""
        if not value:
            return cls.UNKNOWN
        if isinstance(value, cls):
            return value
        val = getattr(value, "value", str(value)).strip().lower()
        if "easy" in val:
            return cls.EASY
        if "medium" in val or "med" in val:
            return cls.MEDIUM
        if "hard" in val:
            return cls.HARD
        return cls.UNKNOWN


class Platform(str, Enum):
    """Problem source platform."""

    LEETCODE = "LeetCode"
    HACKERRANK = "HackerRank"
    CODEFORCES = "Codeforces"
    CUSTOM = "Custom"


class NoteType(str, Enum):
    """Category of problem note."""

    INTUITION = "Intuition"
    BUG_PATTERN = "Bug Pattern"
    COMPLEXITY = "Complexity Analysis"
    GENERAL = "General"
