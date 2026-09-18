"""Personal pattern recognition analyzer for DSA problem solving."""

from datetime import datetime, timezone
from typing import Any, Sequence

from pydantic import BaseModel, Field

from codememory.analytics.analytics_service import AnalyticsService
from codememory.domain.enums import SubmissionStatus
from codememory.domain.models import Problem


class PatternAnalysisResult(BaseModel):
    """Structured result containing detected personal problem-solving patterns."""

    weak_topics: list[dict[str, float | str | int]] = Field(default_factory=list)
    high_failure_topics: list[dict[str, float | str | int]] = Field(default_factory=list)
    repeated_tle_problems: list[str] = Field(default_factory=list)
    repeated_wa_problems: list[str] = Field(default_factory=list)
    brute_force_before_optimized_problems: list[str] = Field(default_factory=list)
    high_attempt_problems: list[dict[str, Any]] = Field(default_factory=list)
    unpracticed_topics: list[dict[str, int | str]] = Field(default_factory=list)
    most_used_languages: list[str] = Field(default_factory=list)


class PatternAnalyzer:
    """Analyzer detecting learning patterns, struggle areas, and practice gaps."""

    def __init__(self, analytics_service: AnalyticsService):
        self.analytics = analytics_service

    def analyze(self, unpracticed_days_threshold: int = 14) -> PatternAnalysisResult:
        """Run complete pattern analysis across stored problems and attempts."""
        problems = self.analytics._get_all_problems()
        result = PatternAnalysisResult()

        if not problems:
            return result

        now = datetime.now(timezone.utc)

        # 1. Topic performance patterns
        topic_stats = self.analytics.get_topic_statistics()
        for ts in topic_stats:
            if ts.total_problems >= 1:
                if ts.success_rate_pct < 50.0:
                    result.weak_topics.append(
                        {
                            "topic": ts.topic,
                            "success_rate_pct": ts.success_rate_pct,
                            "total_problems": ts.total_problems,
                        }
                    )
                if ts.acceptance_rate_pct < 40.0:
                    result.high_failure_topics.append(
                        {
                            "topic": ts.topic,
                            "acceptance_rate_pct": ts.acceptance_rate_pct,
                            "total_submissions": ts.total_submissions,
                        }
                    )

        # 2. Problem level pattern detection
        topic_last_dates: dict[str, datetime] = {}

        for p in problems:
            tle_count = 0
            wa_count = 0
            has_accepted = p.latest_accepted_submission is not None
            first_att_failed = len(p.attempts) > 0 and not p.attempts[0].is_accepted

            for a in p.attempts:
                for s in a.submissions:
                    if s.status == SubmissionStatus.TIME_LIMIT_EXCEEDED:
                        tle_count += 1
                    elif s.status == SubmissionStatus.WRONG_ANSWER:
                        wa_count += 1

                    # Track last activity for topics
                    for t in p.topics:
                        t_clean = t.strip()
                        if t_clean:
                            if t_clean not in topic_last_dates or s.submitted_at > topic_last_dates[t_clean]:
                                topic_last_dates[t_clean] = s.submitted_at

            if tle_count >= 2:
                result.repeated_tle_problems.append(p.title)

            if wa_count >= 2:
                result.repeated_wa_problems.append(p.title)

            if first_att_failed and has_accepted:
                result.brute_force_before_optimized_problems.append(p.title)

            if len(p.attempts) >= 2:
                result.high_attempt_problems.append(
                    {
                        "title": p.title,
                        "slug": p.slug,
                        "attempts_count": len(p.attempts),
                        "status": "Solved" if has_accepted else "Unsolved",
                    }
                )

        # 3. Unpracticed topics calculation
        for topic_name, last_dt in topic_last_dates.items():
            days_since = (now - last_dt).days
            if days_since >= unpracticed_days_threshold:
                result.unpracticed_topics.append(
                    {
                        "topic": topic_name,
                        "days_unpracticed": days_since,
                        "last_practiced": last_dt.strftime("%Y-%m-%d"),
                    }
                )
        result.unpracticed_topics.sort(key=lambda item: item["days_unpracticed"], reverse=True)

        # 4. Frequent languages
        lang_stats = self.analytics.get_language_statistics()
        result.most_used_languages = [ls.language for ls in lang_stats[:3]]

        return result
