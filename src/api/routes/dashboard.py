from fastapi import APIRouter, Depends, Query
from typing import List, Optional

from codememory.core.service import CodeMemoryService
from api.dependencies import get_service
from api.schemas.dashboard import DashboardOut

router = APIRouter(tags=["dashboard"])

@router.get("/dashboard", response_model=DashboardOut)
def get_dashboard(
    account: Optional[str] = Query(default=None, description="Filter submissions by source account (e.g. LeetCode username)."),
    service: CodeMemoryService = Depends(get_service),
):
    """Assemble dashboard data from existing service methods.

    When ``account`` is omitted, all submissions are included. When provided,
    only submissions tagged with that ``source_account`` are counted, allowing
    analytics to be scoped to a single connected LeetCode account.
    """
    overview = service.analytics_service.get_overview(account=account)
    streaks = service.analytics_service.get_streaks(account=account)

    # Update overview streak fields with real data
    overview.current_streak_days = streaks.current_streak_days
    overview.longest_streak_days = streaks.longest_streak_days
    overview.active_days_last_30 = streaks.active_days_last_30

    topics = service.analytics_service.get_topic_statistics(account=account)
    difficulties = service.analytics_service.get_difficulty_statistics(account=account)
    languages = service.analytics_service.get_language_statistics(account=account)

    progress = service.analytics_service.get_progress_over_time(granularity="day", account=account)

    struggles = service.analytics_service.get_struggle_problems(limit=5, account=account)

    # Revision queue limit to 5
    revision_queue = service.revision_service.get_revision_queue(limit=5)

    # Real activity heatmaps and timeline events
    activity = service.analytics_service.get_activity_heatmap(account=account)
    timeline = service.analytics_service.get_timeline_events(limit=14, account=account)

    return DashboardOut(
        overview=overview.model_dump(mode="json"),
        activity=[a.model_dump(mode="json") for a in activity],
        timeline=[t.model_dump(mode="json") for t in timeline],
        struggles=[s.model_dump(mode="json") for s in struggles],
        topics=[t.model_dump(mode="json") for t in topics],
        languages=[l.model_dump(mode="json") for l in languages],
        difficulties=[d.model_dump(mode="json") for d in difficulties],
        revision_queue=[r.model_dump(mode="json") for r in revision_queue],
        progress=[p.model_dump(mode="json") for p in progress]
    )
