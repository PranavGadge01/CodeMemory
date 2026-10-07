from fastapi import APIRouter, Depends, Query
from typing import Optional
from codememory.core.service import CodeMemoryService

from api.dependencies import get_service
from api.schemas.analytics import AnalyticsOut

router = APIRouter(tags=["analytics"])

@router.get("/analytics", response_model=AnalyticsOut)
def get_analytics(
    granularity: str = Query("day", description="day, week, or month"),
    service: CodeMemoryService = Depends(get_service),
):
    """Get full system analytics.

    When a LeetCode account is connected, analytics are scoped to that account.
    """
    safe_granularity = granularity if granularity in ["day", "week", "month"] else "day"
    account = service.active_account
    # One history expansion shared by every analytics call below.
    snapshot = service.history_snapshot()

    return AnalyticsOut(
        overview=service.analytics_service.get_overview(account=account, snapshot=snapshot).model_dump(),
        topics=[t.model_dump() for t in service.analytics_service.get_topic_statistics(account=account, snapshot=snapshot)],
        difficulties=[d.model_dump() for d in service.analytics_service.get_difficulty_statistics(account=account, snapshot=snapshot)],
        languages=[l.model_dump() for l in service.analytics_service.get_language_statistics(account=account)],
        progress=[p.model_dump() for p in service.analytics_service.get_progress_over_time(granularity=safe_granularity, account=account, snapshot=snapshot)],
        struggles=[s.model_dump() for s in service.analytics_service.get_struggle_problems(limit=10, account=account, snapshot=snapshot)]
    )
