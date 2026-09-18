"""Structured Pydantic models for AI analysis output and records."""

from datetime import datetime, timezone
from typing import Any, List, Optional
from pydantic import BaseModel, Field, computed_field


class SubmissionAnalysis(BaseModel):
    """Structured result for a single submission attempt analysis."""

    approach: str = Field(description="Inferred algorithmic approach or design pattern")
    algorithms: List[str] = Field(default_factory=list, description="Primary algorithms present")
    data_structures: List[str] = Field(default_factory=list, description="Primary data structures present")
    inferred_pattern: str = Field(description="Inferred problem-solving pattern")
    time_complexity: str = Field(description="Big-O time complexity")
    space_complexity: str = Field(description="Big-O space complexity")
    correctness_summary: str = Field(description="Summary of correctness or failure type")
    potential_issues: Optional[str] = Field(default=None, description="Potential flaws, overflow risk, or edge-case bugs")
    strengths: Optional[str] = Field(default=None, description="What was executed well in this submission")
    weaknesses: Optional[str] = Field(default=None, description="Weaknesses or inefficiency in the solution")
    concise_explanation: str = Field(description="Concise summary explanation of the submission code design")
    certain_facts: List[str] = Field(default_factory=list, description="Empirical facts directly observable from code/metadata")
    likely_explanations: List[str] = Field(default_factory=list, description="Hypothesized explanations requiring verification")
    analysis_version: str = Field(default="v1", description="Version of the prompt/schema used for analysis")

    # Backward-compatible computed fields for legacy Phase 5 calls
    @computed_field
    def inferred_approach(self) -> str:
        return self.approach

    @computed_field
    def algorithm_ds(self) -> str:
        items = self.algorithms + self.data_structures
        return ", ".join(items) if items else self.approach

    @computed_field
    def possible_mistake(self) -> Optional[str]:
        return self.potential_issues or (self.likely_explanations[0] if self.likely_explanations else None)

    @computed_field
    def improvement_over_previous(self) -> Optional[str]:
        return self.strengths or (self.certain_facts[0] if self.certain_facts else None)

    @computed_field
    def key_insight(self) -> str:
        return self.concise_explanation


class EvolutionStepDetail(BaseModel):
    """Single attempt detail within a solution evolution sequence."""

    attempt_number: int
    submission_id: str
    status: str
    approach: str
    time_complexity: str
    space_complexity: str
    runtime_ms: Optional[float] = None
    memory_mb: Optional[float] = None
    key_change_from_prev: Optional[str] = None


class SolutionEvolution(BaseModel):
    """Structured result for multi-attempt solution evolution analysis."""

    problem_id: str
    problem_title: str
    total_attempts: int
    initial_approach: str
    final_approach: str
    major_changes: List[str] = Field(default_factory=list)
    optimization_steps: List[str] = Field(default_factory=list)
    mistakes_identified: List[str] = Field(default_factory=list)
    learning_points: List[str] = Field(default_factory=list)
    overall_summary: str
    steps: List[EvolutionStepDetail] = Field(default_factory=list)
    analysis_version: str = Field(default="v1", description="Version of evolution analysis prompt/schema")


class AIAnalysisRecord(BaseModel):
    """Stored database record of a cached AI submission analysis."""

    id: str
    submission_id: str
    code_hash: str
    analysis_version: str
    analysis_data: dict[str, Any]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
