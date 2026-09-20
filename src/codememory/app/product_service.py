"""ProductService facade layer aggregating existing services for UI consumption."""

from datetime import datetime, timedelta, timezone
from typing import Optional, Sequence

from codememory.app.product_models import (
    ActivityData,
    AnalyticsData,
    DashboardData,
    KnowledgeData,
    ProblemView,
    SubmissionView,
)
from codememory.core.service import CodeMemoryService
from codememory.domain.enums import DifficultyLevel, SubmissionStatus
from codememory.domain.models import Problem, Submission


class ProductService:
    """Facade service layer providing clean, UI-friendly data access."""

    def __init__(self, service: CodeMemoryService):
        """Initialize ProductService with CodeMemoryService instance."""
        self.service = service

    # ========== Dashboard ==========

    def get_dashboard(self, user_id: str = "default") -> DashboardData:
        """Get dashboard data: metrics, streak, and activity."""
        try:
            overview = self.service.analytics_service.get_overview()

            # Get all submissions for streak calculation
            streak = self._calculate_streak()

            # Get activity data
            activity = self._get_activity_data()

            return DashboardData(
                solved_count=overview.accepted_problems,
                submission_count=overview.total_submissions,
                streak=streak,
                activity=activity,
                overview=overview,
            )
        except Exception:
            return DashboardData()

    def _calculate_streak(self) -> int:
        """Calculate current streak (consecutive days with activity)."""
        problems = self.service.list_problems()
        if not problems:
            return 0

        # Collect all submission dates
        submission_dates = set()
        for problem in problems:
            for attempt in problem.attempts:
                for submission in attempt.submissions:
                    dt = submission.submitted_at
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    submission_dates.add(dt.date())

        if not submission_dates:
            return 0

        # Sort dates and find longest consecutive sequence
        sorted_dates = sorted(submission_dates)
        max_streak = 1
        current_streak = 1
        today = datetime.now(timezone.utc).date()

        for i in range(1, len(sorted_dates)):
            if sorted_dates[i] - sorted_dates[i - 1] == timedelta(days=1):
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 1

        # Bonus: if today or yesterday had activity, extend streak
        if sorted_dates[-1] == today or sorted_dates[-1] == today - timedelta(days=1):
            return max_streak

        return max_streak

    def _get_activity_data(self) -> list[ActivityData]:
        """Get activity data for dashboard."""
        try:
            progress = self.service.analytics_service.get_progress_over_time(granularity="day")
            return [
                ActivityData(
                    date=p.period,
                    problems_solved=p.problems_solved,
                    total_submissions=p.total_submissions,
                    accepted_submissions=p.accepted_submissions,
                )
                for p in progress
            ]
        except Exception:
            return []

    # ========== Problems ==========

    def get_problems(
        self,
        user_id: str = "default",
        difficulty: Optional[str] = None,
        topic: Optional[str] = None,
        solved: Optional[bool] = None,
        language: Optional[str] = None,
    ) -> list[ProblemView]:
        """Get filtered problems."""
        problems = self.service.list_problems()
        filtered = []

        for problem in problems:
            # Difficulty filter
            if difficulty is not None:
                diff_str = problem.difficulty.value if hasattr(problem.difficulty, "value") else str(problem.difficulty)
                if diff_str.lower() != difficulty.lower():
                    continue

            # Topic filter
            if topic is not None:
                if topic not in problem.topics:
                    continue

            # Solved filter
            if solved is not None:
                is_solved = problem.latest_accepted_submission is not None
                if is_solved != solved:
                    continue

            # Language filter
            if language is not None:
                langs = self._get_problem_languages(problem)
                if language.lower() not in [l.lower() for l in langs]:
                    continue

            filtered.append(self._problem_to_view(problem))

        return filtered

    def _get_problem_languages(self, problem: Problem) -> list[str]:
        """Extract all languages used in a problem's submissions."""
        languages = set()
        for attempt in problem.attempts:
            for submission in attempt.submissions:
                if submission.language:
                    languages.add(submission.language)
        return sorted(languages)

    def _problem_to_view(self, problem: Problem) -> ProblemView:
        """Convert Problem domain model to ProblemView."""
        is_solved = problem.latest_accepted_submission is not None
        last_attempted = None
        last_solved = None

        if problem.latest_submission:
            last_attempted = problem.latest_submission.submitted_at

        if problem.latest_accepted_submission:
            last_solved = problem.latest_accepted_submission.submitted_at

        # Count submissions and attempts
        submission_count = sum(len(a.submissions) for a in problem.attempts)
        attempt_count = len(problem.attempts)

        return ProblemView(
            id=problem.id,
            title=problem.title,
            slug=problem.slug,
            difficulty=problem.difficulty.value if hasattr(problem.difficulty, "value") else str(problem.difficulty),
            topics=problem.topics,
            platform=problem.platform if isinstance(problem.platform, str) else problem.platform.value,
            url=problem.url,
            solved=is_solved,
            last_attempted_at=last_attempted,
            last_solved_at=last_solved,
            attempt_count=attempt_count,
            submission_count=submission_count,
            languages=self._get_problem_languages(problem),
        )

    # ========== Submissions ==========

    def get_submissions(
        self,
        user_id: str = "default",
        problem_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[SubmissionView]:
        """Get submission history."""
        submissions: list[tuple[Submission, Problem, int]] = []

        problems = self.service.list_problems()
        for problem in problems:
            # Filter by problem_id if specified
            if problem_id and problem.id != problem_id and problem.slug != problem_id:
                continue

            # Collect submissions with problem context
            for attempt_idx, attempt in enumerate(problem.attempts):
                for submission in attempt.submissions:
                    submissions.append((submission, problem, attempt_idx + 1))

        # Sort by submitted_at descending
        submissions.sort(key=lambda x: x[0].submitted_at, reverse=True)

        # Apply limit
        submissions = submissions[:limit]

        # Convert to SubmissionView
        views = []
        for submission, problem, attempt_number in submissions:
            views.append(
                SubmissionView(
                    id=submission.id,
                    problem_id=problem.id,
                    problem_title=problem.title,
                    code=submission.code,
                    language=submission.language,
                    status=submission.status.value if hasattr(submission.status, "value") else str(submission.status),
                    runtime_ms=submission.runtime_ms,
                    memory_mb=submission.memory_mb,
                    submitted_at=submission.submitted_at,
                    attempt_number=attempt_number,
                    error_message=submission.error_message,
                )
            )

        return views

    # ========== Analytics ==========

    def get_analytics(self, user_id: str = "default") -> AnalyticsData:
        """Get complete analytics data."""
        try:
            overview = self.service.analytics_service.get_overview()
            by_topic = self.service.analytics_service.get_topic_statistics()
            by_difficulty = self.service.analytics_service.get_difficulty_statistics()
            by_language = self.service.analytics_service.get_language_statistics()
            progress = self.service.analytics_service.get_progress_over_time(granularity="day")
            struggle = self.service.analytics_service.get_struggle_problems()

            return AnalyticsData(
                overview=overview,
                by_topic=by_topic,
                by_difficulty=by_difficulty,
                by_language=by_language,
                progress_over_time=progress,
                struggle_problems=struggle,
            )
        except Exception:
            return AnalyticsData()

    # ========== Knowledge / Revision ==========

    def get_knowledge(self, user_id: str = "default") -> KnowledgeData:
        """Get knowledge and revision insights."""
        try:
            # Get pattern analysis
            patterns = self.service.pattern_analyzer.analyze()

            # Get revision queue
            revision_queue = self.service.get_revision_queue(limit=20)

            return KnowledgeData(
                weak_topics=patterns.weak_topics,
                high_failure_topics=patterns.high_failure_topics,
                repeated_tle_problems=patterns.repeated_tle_problems,
                repeated_wa_problems=patterns.repeated_wa_problems,
                high_attempt_problems=patterns.high_attempt_problems,
                improvement_patterns=patterns.improvement_patterns,
                revision_queue=revision_queue,
            )
        except Exception:
            return KnowledgeData()
