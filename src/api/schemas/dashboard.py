from typing import List
from api.schemas.common import BaseCamelModel
from api.schemas.analytics import (
    AnalyticsOverviewOut,
    ActivityDayOut,
    TimelineEventOut,
    StruggleProblemOut,
    TopicStatOut,
    LanguageStatOut,
    DifficultyStatOut,
    ProgressOverTimeOut
)
from api.schemas.revision import RevisionQueueItemOut

class DashboardOut(BaseCamelModel):
    overview: AnalyticsOverviewOut
    activity: List[ActivityDayOut]
    timeline: List[TimelineEventOut]
    struggles: List[StruggleProblemOut]
    topics: List[TopicStatOut]
    languages: List[LanguageStatOut]
    difficulties: List[DifficultyStatOut]
    revision_queue: List[RevisionQueueItemOut]
    progress: List[ProgressOverTimeOut]
