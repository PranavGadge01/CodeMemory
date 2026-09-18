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
    improvement_patterns: list[dict[str, Any]] = Field(default_factory=list)


class PatternAnalyzer:
    """Analyzer detecting learning patterns, struggle areas, and practice gaps."""

    def __init__(self, analytics_service: AnalyticsService):
        self.analytics = analytics_service

    def analyze(
        self,
        unpracticed_days_threshold: int = 14,
        min_topic_problems_threshold: int = 2,
        min_topic_submissions_threshold: int = 3,
        weak_topic_success_threshold: float = 50.0,
        high_failure_acceptance_threshold: float = 40.0,
    ) -> PatternAnalysisResult:
        """Run complete pattern analysis across stored problems and attempts.

        Args:
            unpracticed_days_threshold: Minimum inactive days to flag as unpracticed.
            min_topic_problems_threshold: Minimum total problems required in a topic before flagging as weak.
            min_topic_submissions_threshold: Minimum total submissions required in a topic before flagging as high-failure.
            weak_topic_success_threshold: Success rate percentage below which a topic is considered weak.
            high_failure_acceptance_threshold: Acceptance rate percentage below which a topic is considered high-failure.
        """
        problems = self.analytics._get_all_problems()
        result = PatternAnalysisResult()

        if not problems:
            return result

        now = datetime.now(timezone.utc)

        # 1. Topic performance patterns (Weak topics & High failure topics with sample size checks)
        topic_stats = self.analytics.get_topic_statistics()
        for ts in topic_stats:
            # Weak topics: requires sufficient problem sample size
            if ts.total_problems >= min_topic_problems_threshold and ts.success_rate_pct < weak_topic_success_threshold:
                result.weak_topics.append(
                    {
                        "topic": ts.topic,
                        "success_rate_pct": ts.success_rate_pct,
                        "total_problems": ts.total_problems,
                    }
                )
            # High failure topics: requires sufficient submission sample size
            if ts.total_submissions >= min_topic_submissions_threshold and ts.acceptance_rate_pct < high_failure_acceptance_threshold:
                result.high_failure_topics.append(
                    {
                        "topic": ts.topic,
                        "acceptance_rate_pct": ts.acceptance_rate_pct,
                        "total_submissions": ts.total_submissions,
                    }
                )

        # Deterministic sorting for topics
        result.weak_topics.sort(key=lambda item: (item["success_rate_pct"], -int(item["total_problems"]), str(item["topic"])))
        result.high_failure_topics.sort(key=lambda item: (item["acceptance_rate_pct"], -int(item["total_submissions"]), str(item["topic"])))

        # 2. Problem level pattern detection
        topic_last_dates: dict[str, datetime] = {}

        # Collect problem entries deterministically
        tle_problem_list: list[str] = []
        wa_problem_list: list[str] = []
        bf_problem_list: list[str] = []
        high_attempt_list: list[dict[str, Any]] = []

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
                            s_time = s.submitted_at
                            if s_time.tzinfo is None:
                                s_time = s_time.replace(tzinfo=timezone.utc)
                            if t_clean not in topic_last_dates or s_time > topic_last_dates[t_clean]:
                                topic_last_dates[t_clean] = s_time

            if tle_count >= 2:
                tle_problem_list.append(p.title)

            if wa_count >= 2:
                wa_problem_list.append(p.title)

            if first_att_failed and has_accepted:
                bf_problem_list.append(p.title)

            if len(p.attempts) >= 2:
                high_attempt_list.append(
                    {
                        "title": p.title,
                        "slug": p.slug,
                        "attempts_count": len(p.attempts),
                        "status": "Solved" if has_accepted else "Unsolved",
                    }
                )

        # Deterministic sorting for problem lists
        result.repeated_tle_problems = sorted(tle_problem_list)
        result.repeated_wa_problems = sorted(wa_problem_list)
        result.brute_force_before_optimized_problems = sorted(bf_problem_list)
        result.high_attempt_problems = sorted(
            high_attempt_list,
            key=lambda item: (-item["attempts_count"], 0 if item["status"] == "Unsolved" else 1, item["title"]),
        )

        # 3. Unpracticed topics calculation (Safe timezone handling & deterministic sorting)
        for topic_name, last_dt in topic_last_dates.items():
            dt_aware = last_dt if last_dt.tzinfo is not None else last_dt.replace(tzinfo=timezone.utc)
            days_since = (now - dt_aware).days
            if days_since >= unpracticed_days_threshold:
                result.unpracticed_topics.append(
                    {
                        "topic": topic_name,
                        "days_unpracticed": days_since,
                        "last_practiced": dt_aware.strftime("%Y-%m-%d"),
                    }
                )
        result.unpracticed_topics.sort(key=lambda item: (-int(item["days_unpracticed"]), str(item["topic"])))

        # 4. Frequent languages
        lang_stats = self.analytics.get_language_statistics()
        result.most_used_languages = [ls.language for ls in lang_stats[:3]]

        # 5. Improvement patterns (Deterministic comparison of earlier vs recent activity)
        result.improvement_patterns = self._detect_improvements(problems)

        return result

    def _detect_improvements(self, problems: Sequence[Problem]) -> list[dict[str, Any]]:
        """Detect deterministic improvement patterns comparing earlier vs recent activity."""
        all_submissions = []
        for p in problems:
            for a in p.attempts:
                for s in a.submissions:
                    s_dt = s.submitted_at if s.submitted_at.tzinfo is not None else s.submitted_at.replace(tzinfo=timezone.utc)
                    all_submissions.append((s_dt, s))

        # Require minimum submission sample size to make valid comparisons
        if len(all_submissions) < 6:
            return []

        all_submissions.sort(key=lambda item: item[0])
        mid = len(all_submissions) // 2
        earlier = all_submissions[:mid]
        recent = all_submissions[mid:]

        earlier_acc = sum(1 for _, s in earlier if s.status == SubmissionStatus.ACCEPTED)
        earlier_acc_rate = (earlier_acc / len(earlier)) * 100.0

        recent_acc = sum(1 for _, s in recent if s.status == SubmissionStatus.ACCEPTED)
        recent_acc_rate = (recent_acc / len(recent)) * 100.0

        improvements: list[dict[str, Any]] = []

        # Acceptance rate improvement
        if recent_acc_rate > earlier_acc_rate:
            diff = recent_acc_rate - earlier_acc_rate
            improvements.append(
                {
                    "metric": "acceptance_rate",
                    "earlier_pct": round(earlier_acc_rate, 1),
                    "recent_pct": round(recent_acc_rate, 1),
                    "delta_pct": round(diff, 1),
                    "summary": f"Acceptance rate increased from {earlier_acc_rate:.1f}% to {recent_acc_rate:.1f}% (+{diff:.1f}%).",
                }
            )

        # Average attempts per solved problem comparison
        earlier_end_time = earlier[-1][0]
        solved_earlier: list[int] = []
        solved_recent: list[int] = []

        for p in problems:
            acc_sub = p.latest_accepted_submission
            if acc_sub:
                acc_dt = acc_sub.submitted_at if acc_sub.submitted_at.tzinfo is not None else acc_sub.submitted_at.replace(tzinfo=timezone.utc)
                if acc_dt <= earlier_end_time:
                    solved_earlier.append(len(p.attempts))
                else:
                    solved_recent.append(len(p.attempts))

        if len(solved_earlier) >= 2 and len(solved_recent) >= 2:
            avg_earlier = sum(solved_earlier) / len(solved_earlier)
            avg_recent = sum(solved_recent) / len(solved_recent)
            if avg_recent < avg_earlier:
                diff_attempts = avg_earlier - avg_recent
                improvements.append(
                    {
                        "metric": "attempts_to_solve",
                        "earlier_avg": round(avg_earlier, 2),
                        "recent_avg": round(avg_recent, 2),
                        "delta": round(diff_attempts, 2),
                        "summary": f"Average attempts needed per solved problem decreased from {avg_earlier:.2f} to {avg_recent:.2f}.",
                    }
                )

        return improvements
