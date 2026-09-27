from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from codememory.core.service import CodeMemoryService
from codememory.domain.exceptions import ProblemNotFoundError

from api.dependencies import get_service
from api.schemas.insights import GroundedInsightOut

router = APIRouter(tags=["insights"])


@router.get("/insights", response_model=GroundedInsightOut)
def get_full_profile_insight(
    service: CodeMemoryService = Depends(get_service),
):
    """Get full-profile grounded insight covering overall practice journey."""
    insight = service.get_grounded_insight(account=service.active_account)
    return GroundedInsightOut(**insight.model_dump())


@router.get("/insights/topic/{topic}", response_model=GroundedInsightOut)
def get_topic_insight(
    topic: str,
    service: CodeMemoryService = Depends(get_service),
):
    """Get topic-specific grounded insight."""
    clean_topic = topic.strip()
    if not clean_topic:
        raise HTTPException(status_code=400, detail="Topic name cannot be empty")

    insight = service.get_topic_insight(clean_topic, account=service.active_account)
    return GroundedInsightOut(**insight.model_dump())


@router.get("/insights/problem/{slug}", response_model=GroundedInsightOut)
def get_problem_insight(
    slug: str,
    service: CodeMemoryService = Depends(get_service),
):
    """Get problem-specific grounded insight."""
    clean_slug = slug.strip()
    if not clean_slug:
        raise HTTPException(status_code=400, detail="Problem identifier cannot be empty")

    try:
        insight = service.get_problem_insight(clean_slug, account=service.active_account)
        return GroundedInsightOut(**insight.model_dump())
    except ProblemNotFoundError:
        raise HTTPException(status_code=404, detail=f"Problem not found: '{clean_slug}'")
