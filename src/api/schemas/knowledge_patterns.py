"""Knowledge patterns output DTOs for the Knowledge page.

These types power the Pattern Toolkit and Connections modules,
derived from the user's actual practice history.
"""

from datetime import datetime, timezone
from typing import List
from pydantic import Field

from api.schemas.common import BaseCamelModel


class PatternSummary(BaseCamelModel):
    """A coding technique or approach encountered in practice."""

    id: str
    label: str
    description: str
    problem_count: int = 0
    first_attempt_accepts: int = 0


class PatternRelationship(BaseCamelModel):
    """Two patterns connected by shared problem context."""

    pattern_a: str
    pattern_b: str
    shared_problem_count: int = 0
    relationship: str = "transitive"


class KnowledgePatternsOut(BaseCamelModel):
    """Response for the Knowledge patterns endpoint."""

    patterns: List[PatternSummary] = Field(default_factory=list)
    relationships: List[PatternRelationship] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
