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
    better_approach: Optional[str] = Field(default=None, description="Recommended better/optimal approach or refinement")
    similar_problems: List[str] = Field(default_factory=list, description="Recommended similar problems to practice")
    analysis_version: str = Field(default="v1", description="Version of evolution analysis prompt/schema")


class AIAnalysisRecord(BaseModel):
    """Stored database record of a cached AI submission analysis."""

    id: str
    submission_id: str
    code_hash: str
    analysis_version: str
    analysis_data: dict[str, Any]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Explainable AI & Grounded Learning Models (Features A - E)
# ---------------------------------------------------------------------------

class ComplexityComparison(BaseModel):
    """Before and after complexity comparison."""

    current_time: str = "O(n²)"
    proposed_time: str = "O(n)"
    current_space: str = "O(1)"
    proposed_space: str = "O(n)"
    explanation: str = ""
    assumptions: str = ""


class OptimizationExplanation(BaseModel):
    """Structured explainable optimization breakdown for a problem/submission."""

    problem_slug: str
    submission_id: Optional[str] = None
    current_approach: str
    approach_source: str = "code_analysis"  # "code_analysis" | "metadata" | "notes"
    current_solution_summary: str = ""
    bottleneck: str
    why_it_matters: str
    recommended_approach: str
    why_it_works: str
    complexity_comparison: ComplexityComparison
    transformation_steps: List[str] = Field(default_factory=list)
    tradeoffs: str
    worked_example: Optional[str] = None
    edge_cases: List[str] = Field(default_factory=list)
    when_original_is_acceptable: str = ""
    takeaway: str
    general_pattern: str = ""
    follow_up_question: Optional[str] = None
    evidence_refs: List[str] = Field(default_factory=list)


class AttemptEvolutionAnalysis(BaseModel):
    """Structured chronological narrative across multiple attempts for a problem."""

    problem_slug: str
    problem_title: str
    has_code_snapshots: bool = False
    timeline: List[dict[str, Any]] = Field(default_factory=list)
    changes_between_attempts: List[str] = Field(default_factory=list)
    improvements: List[str] = Field(default_factory=list)
    regressions: List[str] = Field(default_factory=list)
    unresolved_issues: List[str] = Field(default_factory=list)
    learning_summary: str
    recommended_next_action: str
    evidence_refs: List[str] = Field(default_factory=list)


class SubmissionPatternFinding(BaseModel):
    """Single structured observation in the overall submission pattern analysis."""

    title: str
    observation: str
    category: str = "fact"  # "fact" | "interpretation" | "recommendation" | "caveat"
    metric_or_examples: str
    why_it_matters: str
    suggested_action: str
    evidence_refs: List[str] = Field(default_factory=list)


class SubmissionPatternInsights(BaseModel):
    """Structured comprehensive learning analysis across all submissions."""

    summary: str
    findings: List[SubmissionPatternFinding] = Field(default_factory=list)
    most_important_gap: str
    evidence_refs: List[str] = Field(default_factory=list)
    sample_size_notes: List[str] = Field(default_factory=list)


class ProblemRecommendation(BaseModel):
    """Deterministic, explainable next LeetCode problem recommendation."""

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


class RoadmapMilestone(BaseModel):
    """Single ordered milestone in a personalized DSA roadmap."""

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
    recommended_problems: List[ProblemRecommendation] = Field(default_factory=list)
    completion_criteria: str
    reflection_question: str
    transition: str = ""
    next_milestone_id: Optional[str] = None
    status: str = "not_started"  # "not_started" | "in_progress" | "completed" | "deferred"
    evidence_refs: List[str] = Field(default_factory=list)


class PersonalizedRoadmap(BaseModel):
    """Personalized DSA roadmap based on observed gaps and learning goals."""

    title: str = "Personalized DSA Mastery Roadmap"
    description: str = ""
    learning_profile_summary: str = ""
    overall_rationale: str = ""
    milestones: List[RoadmapMilestone] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    is_early_stage: bool = True
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    evidence_id: str = ""
    is_read_only: bool = True


# ---------------------------------------------------------------------------
# Collective & per-submission learning insights (evidence hierarchy)
# ---------------------------------------------------------------------------


class LearningInsightItem(BaseModel):
    """A single structured learning insight with an explicit evidence hierarchy.

    ``category`` records which level of the hierarchy this item represents:
    ``fact`` (directly observed), ``pattern`` (derived from multiple facts),
    ``interpretation`` (what the pattern likely means) or ``action`` (what to
    do next).  Interpretations are never presented as facts: each carries its
    own ``evidence`` string so the UI can show the observation and the reading
    of it separately.
    """

    category: str = "fact"  # "fact" | "pattern" | "interpretation" | "action"
    title: str
    summary: str
    evidence: str = ""
    impact: str = ""
    interpretation: str = ""
    action: str = ""
    priority: str = "medium"  # "high" | "medium" | "low"
    confidence: str = "early_signal"  # "recurring" | "early_signal"
    topics: List[str] = Field(default_factory=list)
    examples: List[str] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)


class LearningProgressTrend(BaseModel):
    """A concrete earlier-vs-recent comparison computed from real timestamps."""

    metric: str
    earlier: str
    recent: str
    delta: str = ""
    summary: str
    evidence_refs: List[str] = Field(default_factory=list)


class CollectiveLearningProfile(BaseModel):
    """Deterministic snapshot of the user's complete recorded practice history."""

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


class CollectiveLearningInsight(BaseModel):
    """Structured, evidence-backed analysis of the user's entire history.

    Answers "what have I learned from solving all these problems?" -- distinct
    from the per-submission analysis that answers "what should I learn from
    this specific attempt?".
    """

    scope: str = "full_profile"
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    overall_summary: str = ""
    profile: CollectiveLearningProfile = Field(default_factory=CollectiveLearningProfile)
    strengths: List[LearningInsightItem] = Field(default_factory=list)
    weaknesses: List[LearningInsightItem] = Field(default_factory=list)
    recurring_mistakes: List[LearningInsightItem] = Field(default_factory=list)
    optimization_trends: List[LearningInsightItem] = Field(default_factory=list)
    progress: List[LearningProgressTrend] = Field(default_factory=list)
    focus_areas: List[LearningInsightItem] = Field(default_factory=list)
    recommended_actions: List[str] = Field(default_factory=list)
    practice_next: List["ProblemRecommendation"] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    is_early_stage: bool = True
    evidence_id: str = ""
    evidence_refs: List[str] = Field(default_factory=list)


class SubmissionImprovement(BaseModel):
    """One concrete, actionable improvement for a submission."""

    title: str
    what: str
    why: str
    how: str
    evidence_refs: List[str] = Field(default_factory=list)


class AttemptComparison(BaseModel):
    """Deterministic comparison of a submission against the prior attempt."""

    available: bool = False
    previous_submission_id: Optional[str] = None
    previous_status: Optional[str] = None
    current_status: Optional[str] = None
    summary: str = ""
    changes: List[str] = Field(default_factory=list)
    improvement: str = ""
    lesson: str = ""
    evidence_refs: List[str] = Field(default_factory=list)


class SubmissionLearningAnalysis(BaseModel):
    """Structured per-submission learning analysis ("what should I learn here?")."""

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
    improvements: List[SubmissionImprovement] = Field(default_factory=list)
    current_approach: str = ""
    current_time_complexity: str = "Unknown"
    current_space_complexity: str = "Unknown"
    complexity_source: str = "unavailable"  # "code_analysis" | "metadata" | "unavailable"
    alternative_approach: str = ""
    alternative_time_complexity: str = ""
    alternative_space_complexity: str = ""
    tradeoffs: str = ""
    edge_cases: List[str] = Field(default_factory=list)
    cross_problem_connections: List[str] = Field(default_factory=list)
    previous_attempt_comparison: AttemptComparison = Field(default_factory=AttemptComparison)
    lesson: str = ""
    next_action: str = ""
    general_pattern: str = ""
    has_code: bool = False
    limitations: List[str] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)

