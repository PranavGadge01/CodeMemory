"""Output DTOs for the explainable AI learning endpoints.

These mirror the domain models in codememory.ai.models, providing a stable
typed contract between FastAPI route handlers and the frontend.
"""

from datetime import datetime, timezone
from typing import Any, List, Optional
from pydantic import BaseModel, Field



class ComplexityComparisonOut(BaseModel):
    current_time: str
    proposed_time: str
    current_space: str
    proposed_space: str
    explanation: str
    assumptions: str


class OptimizationExplanationOut(BaseModel):
    problem_slug: str
    submission_id: Optional[str] = None
    current_approach: str
    approach_source: str
    current_solution_summary: str = ""
    bottleneck: str
    why_it_matters: str
    recommended_approach: str
    why_it_works: str
    complexity_comparison: ComplexityComparisonOut
    transformation_steps: List[str] = Field(default_factory=list)
    tradeoffs: str
    worked_example: Optional[str] = None
    edge_cases: List[str] = Field(default_factory=list)
    when_original_is_acceptable: str = ""
    takeaway: str
    general_pattern: str = ""
    follow_up_question: Optional[str] = None
    evidence_refs: List[str] = Field(default_factory=list)


class AttemptEvolutionAnalysisOut(BaseModel):
    problem_slug: str
    problem_title: str
    has_code_snapshots: bool
    timeline: List[dict[str, Any]] = Field(default_factory=list)
    changes_between_attempts: List[str] = Field(default_factory=list)
    improvements: List[str] = Field(default_factory=list)
    regressions: List[str] = Field(default_factory=list)
    unresolved_issues: List[str] = Field(default_factory=list)
    learning_summary: str
    recommended_next_action: str
    evidence_refs: List[str] = Field(default_factory=list)


class SubmissionPatternFindingOut(BaseModel):
    title: str
    observation: str
    category: str
    metric_or_examples: str
    why_it_matters: str
    suggested_action: str
    evidence_refs: List[str] = Field(default_factory=list)


class SubmissionPatternInsightsOut(BaseModel):
    summary: str
    findings: List[SubmissionPatternFindingOut] = Field(default_factory=list)
    most_important_gap: str
    evidence_refs: List[str] = Field(default_factory=list)
    sample_size_notes: List[str] = Field(default_factory=list)


class ProblemRecommendationOut(BaseModel):
    problem_slug: str
    title: str
    difficulty: str
    topics: List[str] = Field(default_factory=list)
    url: Optional[str] = None
    is_revision: bool = False
    selection_rationale: str
    target_skill: str
    prior_attempt_connection: str
    difficulty_rationale: str
    solving_focus: str
    reflection_checklist: List[str] = Field(default_factory=list)
    next_step_after: str
    evidence_refs: List[str] = Field(default_factory=list)
    similarity_reasons: List[str] = Field(default_factory=list)
    source: str = "local_catalog"
    source_problem_slug: Optional[str] = None


class NextProblemsOut(BaseModel):
    recommendations: List[ProblemRecommendationOut] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RoadmapMilestoneOut(BaseModel):
    id: str
    title: str
    order: int
    learning_objective: str
    relevance: str
    objective: str = ""
    rationale: str = ""
    prerequisites: List[str] = Field(default_factory=list)
    concepts_to_study: List[str] = Field(default_factory=list)
    target_skills: List[str] = Field(default_factory=list)
    recommended_problems: List[ProblemRecommendationOut] = Field(default_factory=list)
    completion_criteria: str
    reflection_question: str
    transition: str = ""
    next_milestone_id: Optional[str] = None
    status: str
    evidence_refs: List[str] = Field(default_factory=list)


class PersonalizedRoadmapOut(BaseModel):
    title: str
    description: str
    learning_profile_summary: str = ""
    overall_rationale: str = ""
    milestones: List[RoadmapMilestoneOut] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    is_early_stage: bool = True
    generated_at: datetime
    evidence_id: str
    is_read_only: bool = True


class LearningInsightItemOut(BaseModel):
    category: str
    title: str
    summary: str
    evidence: str = ""
    impact: str = ""
    interpretation: str = ""
    action: str = ""
    priority: str = "medium"
    confidence: str = "early_signal"
    topics: List[str] = Field(default_factory=list)
    examples: List[str] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)


class LearningProgressTrendOut(BaseModel):
    metric: str
    earlier: str
    recent: str
    delta: str = ""
    summary: str
    evidence_refs: List[str] = Field(default_factory=list)


class CollectiveLearningProfileOut(BaseModel):
    total_problems: int = 0
    total_attempted: int = 0
    total_solved: int = 0
    total_submissions: int = 0
    total_attempts: int = 0
    acceptance_rate_pct: float = 0.0
    first_attempt_acceptance_rate_pct: float = 0.0
    avg_attempts_per_solved_problem: float = 0.0
    difficulty_solved: dict[str, int] = Field(default_factory=dict)
    topic_observations: List[dict[str, Any]] = Field(default_factory=list)
    language_share: List[dict[str, Any]] = Field(default_factory=list)
    patterns_practiced: List[str] = Field(default_factory=list)
    complexity_signals: List[dict[str, Any]] = Field(default_factory=list)


class CollectiveLearningInsightOut(BaseModel):
    scope: str
    generated_at: datetime
    overall_summary: str = ""
    profile: CollectiveLearningProfileOut
    strengths: List[LearningInsightItemOut] = Field(default_factory=list)
    weaknesses: List[LearningInsightItemOut] = Field(default_factory=list)
    recurring_mistakes: List[LearningInsightItemOut] = Field(default_factory=list)
    optimization_trends: List[LearningInsightItemOut] = Field(default_factory=list)
    progress: List[LearningProgressTrendOut] = Field(default_factory=list)
    focus_areas: List[LearningInsightItemOut] = Field(default_factory=list)
    recommended_actions: List[str] = Field(default_factory=list)
    practice_next: List[ProblemRecommendationOut] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    is_early_stage: bool = True
    evidence_id: str = ""
    evidence_refs: List[str] = Field(default_factory=list)


class SubmissionImprovementOut(BaseModel):
    title: str
    what: str
    why: str
    how: str
    evidence_refs: List[str] = Field(default_factory=list)


class AttemptComparisonOut(BaseModel):
    available: bool = False
    previous_submission_id: Optional[str] = None
    previous_status: Optional[str] = None
    current_status: Optional[str] = None
    summary: str = ""
    changes: List[str] = Field(default_factory=list)
    improvement: str = ""
    lesson: str = ""
    evidence_refs: List[str] = Field(default_factory=list)


class SubmissionLearningAnalysisOut(BaseModel):
    submission_id: str
    problem_id: str
    problem_slug: str
    problem_title: str
    difficulty: str = "Unknown"
    topics: List[str] = Field(default_factory=list)
    status: str = "Unknown"
    language: str = ""
    overview: str = ""
    what_went_well: List[str] = Field(default_factory=list)
    improvements: List[SubmissionImprovementOut] = Field(default_factory=list)
    current_approach: str = ""
    current_time_complexity: str = "Unknown"
    current_space_complexity: str = "Unknown"
    complexity_source: str = "unavailable"
    alternative_approach: str = ""
    alternative_time_complexity: str = ""
    alternative_space_complexity: str = ""
    tradeoffs: str = ""
    edge_cases: List[str] = Field(default_factory=list)
    cross_problem_connections: List[str] = Field(default_factory=list)
    previous_attempt_comparison: AttemptComparisonOut
    lesson: str = ""
    next_action: str = ""
    general_pattern: str = ""
    has_code: bool = False
    limitations: List[str] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)
