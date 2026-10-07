"""FastAPI routes for explainable AI learning features.

Endpoints:
  GET /api/v1/problems/{slug}/learning-analysis   — attempt evolution
  GET /api/v1/problems/{slug}/optimization        — explainable optimization
  GET /api/v1/learning/patterns                   — submission pattern insights
  GET /api/v1/learning/profile                    — collective learning insight
  GET /api/v1/learning/submissions/{id}           — per-submission learning analysis
  GET /api/v1/learning/recommendations            — next-problem recommendations
  GET /api/v1/learning/roadmap                    — personalized DSA roadmap
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from codememory.core.service import CodeMemoryService
from codememory.domain.exceptions import ProblemNotFoundError

from api.dependencies import get_service
from api.schemas.learning import (
    AttemptEvolutionAnalysisOut,
    CollectiveLearningInsightOut,
    NextProblemsOut,
    OptimizationExplanationOut,
    PersonalizedRoadmapOut,
    SubmissionLearningAnalysisOut,
    SubmissionPatternInsightsOut,
    ProblemRecommendationOut,
    RoadmapMilestoneOut,
    ComplexityComparisonOut,
    SubmissionPatternFindingOut,
)

router = APIRouter(tags=["learning"])


@router.get("/problems/{slug}/learning-analysis", response_model=AttemptEvolutionAnalysisOut)
def get_learning_analysis(
    slug: str,
    service: CodeMemoryService = Depends(get_service),
):
    """Chronological attempt evolution analysis for a specific problem."""
    clean_slug = slug.strip()
    if not clean_slug:
        raise HTTPException(status_code=400, detail="Problem slug cannot be empty.")
    try:
        result = service.get_attempt_evolution_analysis(clean_slug, account=service.active_account)
        return AttemptEvolutionAnalysisOut(**result.model_dump())
    except ProblemNotFoundError:
        raise HTTPException(status_code=404, detail=f"Problem not found: '{clean_slug}'")


@router.get("/problems/{slug}/optimization", response_model=OptimizationExplanationOut)
def get_optimization_explanation(
    slug: str,
    submission_id: Optional[str] = Query(default=None, description="Specific submission ID to analyse"),
    service: CodeMemoryService = Depends(get_service),
):
    """Explainable optimization analysis for a problem (most-recent or specified submission)."""
    clean_slug = slug.strip()
    if not clean_slug:
        raise HTTPException(status_code=400, detail="Problem slug cannot be empty.")
    try:
        result = service.get_optimization_explanation(
            clean_slug,
            submission_id=submission_id,
            account=service.active_account,
        )
        data = result.model_dump()
        data["complexity_comparison"] = ComplexityComparisonOut(**data["complexity_comparison"])
        return OptimizationExplanationOut(**data)
    except ProblemNotFoundError:
        raise HTTPException(status_code=404, detail=f"Problem not found: '{clean_slug}'")


@router.get("/learning/patterns", response_model=SubmissionPatternInsightsOut)
def get_submission_patterns(
    service: CodeMemoryService = Depends(get_service),
):
    """Overall submission pattern insights across the user's full practice history."""
    result = service.get_submission_pattern_insights(account=service.active_account)
    data = result.model_dump()
    data["findings"] = [SubmissionPatternFindingOut(**f) for f in data.get("findings", [])]
    return SubmissionPatternInsightsOut(**data)


@router.get("/learning/profile", response_model=CollectiveLearningInsightOut)
def get_collective_learning_profile(
    service: CodeMemoryService = Depends(get_service),
):
    """Structured collective learning insight derived from the entire history."""
    result = service.get_collective_learning_insight(account=service.active_account)
    data = result.model_dump()
    data["practice_next"] = [ProblemRecommendationOut(**p) for p in data.get("practice_next", [])]
    return CollectiveLearningInsightOut(**data)


@router.get("/learning/submissions/{submission_id}", response_model=SubmissionLearningAnalysisOut)
def get_submission_learning_analysis(
    submission_id: str,
    service: CodeMemoryService = Depends(get_service),
):
    """Structured learning analysis for one submission, with attempt comparison."""
    clean_id = submission_id.strip()
    if not clean_id:
        raise HTTPException(status_code=400, detail="Submission ID cannot be empty.")
    try:
        result = service.get_submission_learning_analysis(
            clean_id, account=service.active_account
        )
        return SubmissionLearningAnalysisOut(**result.model_dump())
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Submission not found: '{clean_id}'")


@router.get("/learning/recommendations", response_model=NextProblemsOut)
def get_next_problem_recommendations(
    limit: int = Query(default=3, ge=1, le=10, description="Number of recommended problems"),
    service: CodeMemoryService = Depends(get_service),
):
    """Ranked next-problem recommendations from the real local catalog."""
    recs = service.get_next_problem_recommendations(limit=limit, account=service.active_account)
    return NextProblemsOut(
        recommendations=[ProblemRecommendationOut(**r.model_dump()) for r in recs]
    )


@router.get("/learning/roadmap", response_model=PersonalizedRoadmapOut)
def get_personalized_roadmap(
    service: CodeMemoryService = Depends(get_service),
):
    """Personalized DSA learning roadmap with ordered milestones."""
    result = service.get_personalized_roadmap(account=service.active_account)
    data = result.model_dump()
    milestones = []
    for m in data.get("milestones", []):
        m["recommended_problems"] = [ProblemRecommendationOut(**p) for p in m.get("recommended_problems", [])]
        milestones.append(RoadmapMilestoneOut(**m))
    data["milestones"] = milestones
    return PersonalizedRoadmapOut(**data)
