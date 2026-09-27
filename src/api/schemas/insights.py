from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class GroundedInsightOut(BaseModel):
    """Stable output DTO for grounded personalized insights."""

    scope: str = Field(description="Insight scope, e.g. 'full_profile', 'topic:Array', 'problem:two-sum'")
    generated_at: datetime = Field(description="Timestamp when evidence was generated")
    headline: str = Field(description="One-sentence headline summary")
    narrative: str = Field(description="Multi-paragraph grounded interpretation")
    key_observations: List[str] = Field(default_factory=list, description="Key empirical observations")
    recommended_actions: List[str] = Field(default_factory=list, description="Actionable recommendations")
    evidence_summary: str = Field(default="", description="Deterministic human-readable evidence summary")
    evidence_refs: List[str] = Field(default_factory=list, description="IDs of specific evidence items referenced")
    confidence_notes: List[str] = Field(default_factory=list, description="Limitations or sample-size notes")
    evidence_id: str = Field(description="The source InsightEvidence.evidence_id uuid")
