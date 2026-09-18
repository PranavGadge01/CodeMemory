"""Data models for raw LeetCode records."""

from typing import Any, List, Optional
from pydantic import BaseModel, Field


class LeetCodeSubmissionRaw(BaseModel):
    """Raw submission data structure from LeetCode exports or API responses."""

    id: Optional[str] = None
    submission_id: Optional[str] = None
    title: str
    title_slug: Optional[str] = None
    problem_id: Optional[str] = None
    question_id: Optional[str] = None
    difficulty: Optional[str] = None
    topics: List[str] = Field(default_factory=list)
    language: str
    code: str = ""
    status: str
    runtime: Optional[str] = None
    memory: Optional[str] = None
    timestamp: Optional[Any] = None
    url: Optional[str] = None
    notes: Optional[str] = None
    reasoning: Optional[str] = None


class LeetCodeProblemRaw(BaseModel):
    """Raw problem metadata from LeetCode."""

    id: Optional[str] = None
    question_id: Optional[str] = None
    title: str
    title_slug: str
    difficulty: Optional[str] = None
    topics: List[str] = Field(default_factory=list)
    url: Optional[str] = None
    content: Optional[str] = None
