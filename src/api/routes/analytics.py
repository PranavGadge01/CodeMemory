from fastapi import APIRouter, Depends, Query
from typing import Optional
from codememory.core.service import CodeMemoryService

from api.dependencies import get_service
from api.schemas.analytics import AnalyticsOut

router = APIRouter(tags=["analytics"])

@router.get("/analytics", response_model=AnalyticsOut)
def get_analytics(
    granularity: str = Query("day", description="day, week, or month"),
    account: Optional[str] = Query(default=None, description="Filter submissions by source account (e.g. LeetCode username)."),
    service: CodeMemoryService = Depends(get_service),
):
    """Get full system analytics.

    When ``account`` is provided, only submissions tagged with that
    ``source_account`` are included in the analytics.
    """
    # Ensure safe granularity fallback if passed an invalid value
    safe_granularity = granularity if granularity in ["day", "week", "month"] else "day"
    
    return AnalyticsOut(
        overview=service.analytics_service.get_overview(account=account).model_dump(),
        topics=[t.model_dump() for t in service.analytics_service.get_topic_statistics(account=account)],
        difficulties=[d.model_dump() for d in service.analytics_service.get_difficulty_statistics(account=account)],
        languages=[l.model_dump() for l in service.analytics_service.get_language_statistics(account=account)],
        progress=[p.model_dump() for p in service.analytics_service.get_progress_over_time(granularity=safe_granularity, account=account)],
        struggles=[s.model_dump() for s in service.analytics_service.get_struggle_problems(limit=10, account=account)]
    )
