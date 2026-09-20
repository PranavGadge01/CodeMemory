from fastapi import APIRouter, Depends
from typing import List

from codememory.core.service import CodeMemoryService
from api.dependencies import get_service
from api.schemas.dashboard import DashboardOut

router = APIRouter(tags=["dashboard"])

@router.get("/dashboard", response_model=DashboardOut)
def get_dashboard(service: CodeMemoryService = Depends(get_service)):
    """Assemble dashboard data from existing service methods."""
    overview = service.analytics_service.get_overview()
    topics = service.analytics_service.get_topic_statistics()
    difficulties = service.analytics_service.get_difficulty_statistics()
    languages = service.analytics_service.get_language_statistics()
    
    # Check if granularity is supported before calling
    # In CodeMemoryService, get_progress_over_time takes granularity string.
    # Defaulting to 'day' to be safe since it exists.
    progress = service.analytics_service.get_progress_over_time(granularity="day")
    
    struggles = service.analytics_service.get_struggle_problems(limit=5)
    
    # Revision queue limit to 5
    revision_queue = service.revision_service.get_revision_queue(limit=5)
    
    return DashboardOut(
        overview=overview.model_dump(),
        activity=[],  # Deferred: No native get_activity_heatmap on service
        timeline=[],  # Deferred: No native get_timeline_events on service
        struggles=[s.model_dump() for s in struggles],
        topics=[t.model_dump() for t in topics],
        languages=[l.model_dump() for l in languages],
        difficulties=[d.model_dump() for d in difficulties],
        revision_queue=[r.model_dump() for r in revision_queue],
        progress=[p.model_dump() for p in progress]
    )
