"""Comprehensive AnalyticsService using DuckDB and Polars."""

import copy
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Sequence, Optional

import polars as pl

from codememory.analytics.analytics_models import (
    ActivityDay,
    AnalyticsOverview,
    AttemptStat,
    DifficultyStat,
    LanguageStat,
    ProgressOverTime,
    StreakInfo,
    StruggleProblem,
    TimelineEvent,
    TopicStat,
)
from codememory.domain.enums import SubmissionStatus
from codememory.domain.models import Problem, _ensure_utc
from codememory.storage.composite_repository import CompositeStorage


class AnalyticsService:
    """Analytical query engine calculating structured metrics over CodeMemory storage."""

    def __init__(self, storage: CompositeStorage):
        self.storage = storage

    def _get_all_problems(self) -> Sequence[Problem]:
        """Fetch all problems from storage."""
        return self.storage.list_all()

    def _filter_problems_by_account(self, problems: Sequence[Problem], account: str | None) -> list[Problem]:
        """Return problems with only the submissions matching ``account``.

        Problems with zero matching submissions are excluded; problems with
        some matching submissions are returned shallow-copied so the caller
        cannot mutate the original domain objects.
        """
        filtered: list[Problem] = []
        for p in problems:
            keep = []
            for a in p.attempts:
                matching = [s for s in a.submissions if s.source_account == account]
                if not matching:
                    continue
                a_copy = copy.copy(a)
                a_copy.submissions = matching
                keep.append(a_copy)
            if not keep:
                continue
            p_copy = copy.copy(p)
            p_copy.attempts = keep
            filtered.append(p_copy)
        return filtered

    @staticmethod
    def _has_leetcode_submissions(problems: Sequence[Problem]) -> bool:
        """Check if any problem has LeetCode-sourced submissions."""
        for p in problems:
            for a in p.attempts:
                for s in a.submissions:
                    if s.source_provider is not None:
                        return True
        return False

    def _scope_problems(self, problems: Sequence[Problem], account: str | None) -> list[Problem]:
        """Apply account scoping to problems for analytics.

        - When ``account`` is a string, filter to that account's submissions.
        - When ``account`` is None and LeetCode data exists, return empty
          (prevent cross-account aggregation).
        - When ``account`` is None and no LeetCode data exists, return all
          (legacy behavior for non-LeetCode data).
        """
        if account is not None:
            return self._filter_problems_by_account(problems, account)
        # No active account: if any LeetCode-sourced submissions exist,
        # return empty to prevent cross-account data exposure.
        if self._has_leetcode_submissions(problems):
            return []
        return list(problems)

    # 1. System Overview Statistics
    def get_overview(self, account: str | None = None) -> AnalyticsOverview:
        """Calculate complete system overview statistics.

        When ``account`` is provided, only submissions from that source account
        are counted (e.g. a specific LeetCode username).
        """
        problems = self._get_all_problems()
        problems = self._scope_problems(problems, account)
        if not problems:
            return AnalyticsOverview()

        total_problems = len(problems)
        total_attempts = 0
        total_submissions = 0
        accepted_submissions = 0
        solved_problems_count = 0
        single_attempt_solved_count = 0
        repeated_problems_count = 0

        attempts_per_solved: list[int] = []
        solving_times_minutes: list[float] = []

        for p in problems:
            p_attempts_count = len(p.attempts)
            total_attempts += p_attempts_count

            if p_attempts_count > 1 or any(len(a.submissions) > 1 for a in p.attempts):
                repeated_problems_count += 1

            all_subs = []
            for a in p.attempts:
                total_submissions += len(a.submissions)
                for s in a.submissions:
                    all_subs.append((a, s))
                    if s.status == SubmissionStatus.ACCEPTED:
                        accepted_submissions += 1

            if p.latest_accepted_submission:
                solved_problems_count += 1
                attempts_per_solved.append(p_attempts_count)

                # First attempt acceptance
                if len(p.attempts) >= 1 and p.attempts[0].is_accepted:
                    single_attempt_solved_count += 1

                # Average solving time calculation
                if len(all_subs) > 1:
                    all_subs.sort(key=lambda item: item[1].submitted_at)
                    first_sub_time = all_subs[0][1].submitted_at
                    accepted_subs = [s for a, s in all_subs if s.status == SubmissionStatus.ACCEPTED]
                    if accepted_subs:
                        first_accepted_time = accepted_subs[0].submitted_at
                        duration = (first_accepted_time - first_sub_time).total_seconds() / 60.0
                        if duration >= 0:
                            solving_times_minutes.append(duration)

        unsolved = total_problems - solved_problems_count
        overall_acc_rate = (accepted_submissions / total_submissions * 100.0) if total_submissions > 0 else 0.0
        avg_attempts_solved = (sum(attempts_per_solved) / len(attempts_per_solved)) if attempts_per_solved else 0.0
        first_attempt_acc_rate = (single_attempt_solved_count / solved_problems_count * 100.0) if solved_problems_count > 0 else 0.0
        repeated_rate = (repeated_problems_count / total_problems * 100.0) if total_problems > 0 else 0.0
        avg_solving_time = (sum(solving_times_minutes) / len(solving_times_minutes)) if solving_times_minutes else None

        return AnalyticsOverview(
            total_problems=total_problems,
            total_attempts=total_attempts,
            total_submissions=total_submissions,
            accepted_problems=solved_problems_count,
            unsolved_problems=unsolved,
            overall_acceptance_rate_pct=round(overall_acc_rate, 2),
            avg_attempts_per_solved_problem=round(avg_attempts_solved, 2),
            first_attempt_acceptance_rate_pct=round(first_attempt_acc_rate, 2),
            repeated_problem_rate_pct=round(repeated_rate, 2),
            avg_solving_time_minutes=round(avg_solving_time, 2) if avg_solving_time is not None else None,
        )

    # 2. Topic Statistics
    def get_topic_statistics(self, account: str | None = None) -> list[TopicStat]:
        """Calculate problem solving metrics grouped by DSA topic."""
        problems = self._get_all_problems()
        if not problems:
            return []
        problems = self._scope_problems(problems, account)
        if not problems:
            return []

        topic_data: dict[str, dict] = defaultdict(
            lambda: {
                "total_problems": 0,
                "solved_problems": 0,
                "total_attempts": 0,
                "total_submissions": 0,
                "accepted_submissions": 0,
            }
        )

        for p in problems:
            topics = p.topics if p.topics else ["Uncategorized"]
            is_solved = p.latest_accepted_submission is not None
            p_attempts = len(p.attempts)

            p_total_subs = 0
            p_acc_subs = 0
            for a in p.attempts:
                p_total_subs += len(a.submissions)
                for s in a.submissions:
                    if s.status == SubmissionStatus.ACCEPTED:
                        p_acc_subs += 1

            for t in topics:
                clean_t = t.strip()
                if not clean_t:
                    continue
                data = topic_data[clean_t]
                data["total_problems"] += 1
                if is_solved:
                    data["solved_problems"] += 1
                data["total_attempts"] += p_attempts
                data["total_submissions"] += p_total_subs
                data["accepted_submissions"] += p_acc_subs

        stats: list[TopicStat] = []
        for topic_name, d in sorted(topic_data.items(), key=lambda item: item[1]["total_problems"], reverse=True):
            acc_rate = (d["accepted_submissions"] / d["total_submissions"] * 100.0) if d["total_submissions"] > 0 else 0.0
            succ_rate = (d["solved_problems"] / d["total_problems"] * 100.0) if d["total_problems"] > 0 else 0.0
            stats.append(
                TopicStat(
                    topic=topic_name,
                    total_problems=d["total_problems"],
                    solved_problems=d["solved_problems"],
                    total_attempts=d["total_attempts"],
                    total_submissions=d["total_submissions"],
                    accepted_submissions=d["accepted_submissions"],
                    acceptance_rate_pct=round(acc_rate, 2),
                    success_rate_pct=round(succ_rate, 2),
                )
            )

        return stats

    # 3. Difficulty Statistics
    def get_difficulty_statistics(self, account: str | None = None) -> list[DifficultyStat]:
        """Calculate problem solving metrics grouped by difficulty."""
        problems = self._get_all_problems()
        problems = self._scope_problems(problems, account)
        diff_data: dict[str, dict] = defaultdict(
            lambda: {
                "total_problems": 0,
                "solved_problems": 0,
                "total_attempts": 0,
                "total_submissions": 0,
                "accepted_submissions": 0,
            }
        )

        for p in problems:
            diff_str = p.difficulty.value if hasattr(p.difficulty, "value") else str(p.difficulty)
            is_solved = p.latest_accepted_submission is not None

            data = diff_data[diff_str]
            data["total_problems"] += 1
            if is_solved:
                data["solved_problems"] += 1
            data["total_attempts"] += len(p.attempts)

            for a in p.attempts:
                data["total_submissions"] += len(a.submissions)
                for s in a.submissions:
                    if s.status == SubmissionStatus.ACCEPTED:
                        data["accepted_submissions"] += 1

        stats: list[DifficultyStat] = []
        for diff_name in ["Easy", "Medium", "Hard", "Unknown"]:
            if diff_name in diff_data:
                d = diff_data[diff_name]
                acc_rate = (d["accepted_submissions"] / d["total_submissions"] * 100.0) if d["total_submissions"] > 0 else 0.0
                stats.append(
                    DifficultyStat(
                        difficulty=diff_name,
                        total_problems=d["total_problems"],
                        solved_problems=d["solved_problems"],
                        total_attempts=d["total_attempts"],
                        total_submissions=d["total_submissions"],
                        accepted_submissions=d["accepted_submissions"],
                        acceptance_rate_pct=round(acc_rate, 2),
                    )
                )

        return stats

    # 4. Language Statistics
    def get_language_statistics(self, account: str | None = None) -> list[LanguageStat]:
        """Calculate submission statistics grouped by programming language using DuckDB."""
        try:
            account_filter = f" AND source_account = '{account}'" if account is not None else " AND source_provider IS NULL"
            query = f"""
                SELECT
                    language,
                    COUNT(id) as total_subs,
                    SUM(CASE WHEN status = 'Accepted' THEN 1 ELSE 0 END) as accepted_subs
                FROM submissions
                WHERE 1=1 {account_filter}
                GROUP BY language
                ORDER BY total_subs DESC;
            """
            rows = self.storage.duckdb_repo.conn.execute(query).fetchall()
        except Exception:
            rows = []

        total_all_subs = sum(int(r[1]) for r in rows) if rows else 0
        stats: list[LanguageStat] = []

        for lang, total_subs, accepted_subs in rows:
            acc_rate = (accepted_subs / total_subs * 100.0) if total_subs > 0 else 0.0
            share = (total_subs / total_all_subs * 100.0) if total_all_subs > 0 else 0.0
            stats.append(
                LanguageStat(
                    language=lang,
                    total_submissions=total_subs,
                    accepted_submissions=accepted_subs,
                    acceptance_rate_pct=round(acc_rate, 2),
                    usage_share_pct=round(share, 2),
                )
            )

        return stats

    # 5. Attempt Statistics & Progression
    def get_attempt_statistics(self, account: str | None = None) -> AttemptStat:
        """Calculate statistics on attempt counts and brute-force->optimized progressions."""
        problems = self._get_all_problems()
        problems = self._scope_problems(problems, account)
        if not problems:
            return AttemptStat()

        total_problems = len(problems)
        total_attempts = sum(len(p.attempts) for p in problems)
        avg_attempts = total_attempts / total_problems if total_problems > 0 else 0.0

        single_solved = 0
        multi_solved = 0
        max_att = 0
        bf_to_opt = 0

        for p in problems:
            p_att_count = len(p.attempts)
            max_att = max(max_att, p_att_count)

            if p.latest_accepted_submission:
                if p_att_count == 1:
                    single_solved += 1
                elif p_att_count > 1:
                    multi_solved += 1

            # Detect brute force to optimized progression:
            # e.g., attempt 1 has TLE (timeout, the classic brute force), followed by a later attempt with Accepted
            # We specifically check for TLE, not WA, because TLE indicates algorithmic inefficiency (brute force)
            if p_att_count > 1 and p.latest_accepted_submission:
                first_att = p.attempts[0]
                if first_att.status == SubmissionStatus.TIME_LIMIT_EXCEEDED:
                    bf_to_opt += 1

        return AttemptStat(
            total_attempts=total_attempts,
            avg_attempts_per_problem=round(avg_attempts, 2),
            single_attempt_solved_count=single_solved,
            multiple_attempt_solved_count=multi_solved,
            max_attempts_single_problem=max_att,
            brute_force_to_optimized_count=bf_to_opt,
        )

    # 6. Progress Over Time
    def get_progress_over_time(self, granularity: str = "day", account: str | None = None) -> list[ProgressOverTime]:
        """Aggragate solved problems and submission counts over time using Polars."""
        problems = self._get_all_problems()
        problems = self._scope_problems(problems, account)
        rows: list[dict] = []

        for p in problems:
            for a in p.attempts:
                for s in a.submissions:
                    rows.append(
                        {
                            "problem_id": p.id,
                            "submitted_at": s.submitted_at.replace(tzinfo=None) if isinstance(s.submitted_at, datetime) else s.submitted_at,
                            "status": s.status.value if hasattr(s.status, "value") else str(s.status),
                        }
                    )

        if not rows:
            return []

        df = pl.DataFrame(rows)

        # Truncate dates according to granularity
        if granularity == "month":
            df = df.with_columns(pl.col("submitted_at").dt.truncate("1mo").dt.strftime("%Y-%m").alias("period"))
        elif granularity == "week":
            df = df.with_columns(pl.col("submitted_at").dt.strftime("%Y-W%V").alias("period"))
        else:  # day
            df = df.with_columns(pl.col("submitted_at").dt.strftime("%Y-%m-%d").alias("period"))

        aggregated = (
            df.group_by("period")
            .agg(
                [
                    pl.col("status").count().alias("total_submissions"),
                    (pl.col("status") == "Accepted").sum().alias("accepted_submissions"),
                    pl.col("problem_id").filter(pl.col("status") == "Accepted").n_unique().alias("problems_solved"),
                ]
            )
            .sort("period")
        )

        results: list[ProgressOverTime] = []
        for r in aggregated.iter_rows(named=True):
            results.append(
                ProgressOverTime(
                    period=r["period"],
                    problems_solved=r["problems_solved"],
                    total_submissions=r["total_submissions"],
                    accepted_submissions=r["accepted_submissions"],
                )
            )

        return results

    # 7. Struggle Problems
    def get_struggle_problems(self, limit: int = 10, account: str | None = None) -> list[StruggleProblem]:
        """Identify problems with high failure rates or multiple failed attempts."""
        problems = self._get_all_problems()
        problems = self._scope_problems(problems, account)
        struggles: list[StruggleProblem] = []

        for p in problems:
            failed_attempts = 0
            failed_subs = 0
            for a in p.attempts:
                if not a.is_accepted:
                    failed_attempts += 1
                for s in a.submissions:
                    if s.status != SubmissionStatus.ACCEPTED:
                        failed_subs += 1

            if failed_attempts > 0 or failed_subs > 0 or len(p.attempts) > 1 or not p.latest_accepted_submission:
                status_str = "Solved" if p.latest_accepted_submission else "Unsolved"
                diff_str = p.difficulty.value if hasattr(p.difficulty, "value") else str(p.difficulty)
                struggles.append(
                    StruggleProblem(
                        problem_id=p.id,
                        title=p.title,
                        slug=p.slug,
                        difficulty=diff_str,
                        total_attempts=len(p.attempts),
                        failed_attempts=failed_attempts,
                        failed_submissions=failed_subs,
                        status=status_str,
                        topics=p.topics,
                    )
                )

        # Sort by Unsolved status first, then failed attempts, failed submissions, total attempts
        struggles.sort(key=lambda s: (s.status == "Unsolved", s.failed_attempts, s.failed_submissions, s.total_attempts), reverse=True)
        return struggles[:limit]

    # 8. Activity Heatmap
    def get_activity_heatmap(self, days: int = 90, account: str | None = None) -> list[ActivityDay]:
        """Compute daily activity metrics from stored submissions.

        Returns one entry per day that has actual activity — no fabricated zero days.
        When ``account`` is provided, only submissions from that source account are
        counted (e.g. a specific LeetCode username).
        """
        account_filter = f" AND source_account = '{account}'" if account is not None else " AND source_provider IS NULL"
        query = f"""
            SELECT
                strftime(DATE(submitted_at), '%Y-%m-%d') as day,
                COUNT(*) as total_subs,
                SUM(CASE WHEN status = 'Accepted' THEN 1 ELSE 0 END) as accepted_subs,
                COUNT(DISTINCT problem_id) as problems_solved
            FROM submissions
            WHERE DATE(submitted_at) >= (CURRENT_DATE - INTERVAL '{days}' DAY)
            AND 1=1 {account_filter}
            GROUP BY day
            ORDER BY day;
        """
        try:
            rows = self.storage.duckdb_repo.conn.execute(query).fetchall()
        except Exception:
            return []

        results: list[ActivityDay] = []
        for day_str, total_subs, accepted_subs, problems_solved in rows:
            results.append(
                ActivityDay(
                    date=day_str,
                    submissions=int(total_subs),
                    accepted=int(accepted_subs),
                    solved=int(problems_solved),
                    minutes_active=0,
                )
            )
        return results

    # 9. Streak Calculation
    def get_streaks(self, account: str | None = None) -> StreakInfo:
        """Calculate current and longest streak from actual submission dates.

        A day is 'active' if at least one submission was made on that UTC date.
        Streaks are computed backwards from 'today' for the current streak.
        When ``account`` is provided, only submissions from that source account
        are considered.
        """
        account_filter = f"WHERE source_account = '{account}'" if account is not None else "WHERE source_provider IS NULL"
        query = f"""
            SELECT DISTINCT CAST(strftime(submitted_at, '%Y-%m-%d') AS VARCHAR) as day
            FROM submissions
            {account_filter}
            ORDER BY day DESC;
        """
        try:
            rows = self.storage.duckdb_repo.conn.execute(query).fetchall()
        except Exception:
            return StreakInfo()

        if not rows:
            return StreakInfo()

        active_dates: set[str] = set()
        for (day_str,) in rows:
            if isinstance(day_str, str):
                active_dates.add(day_str)

        today = datetime.now(timezone.utc).date()
        sorted_dates = sorted(
            (datetime.strptime(d, "%Y-%m-%d").date() for d in active_dates),
            reverse=True,
        )

        if not sorted_dates:
            return StreakInfo()

        # Compute current streak (consecutive days ending at the most recent active date)
        current = 0
        for i in range(len(sorted_dates)):
            expected_date = sorted_dates[0] - timedelta(days=i)
            if expected_date.isoformat() in active_dates:
                current = i + 1
            else:
                break

        # Compute longest streak
        longest = 1
        current_run = 1
        for i in range(1, len(sorted_dates)):
            prev = sorted_dates[i - 1]
            curr = sorted_dates[i]
            if (prev - curr).days == 1:
                current_run += 1
                longest = max(longest, current_run)
            else:
                current_run = 1

        # Active days in last 30 days
        cutoff = today - timedelta(days=29)
        active_last_30 = sum(
            1 for d in active_dates
            if datetime.strptime(d, "%Y-%m-%d").date() >= cutoff
        )

        return StreakInfo(
            current_streak_days=current,
            longest_streak_days=longest,
            active_days_last_30=active_last_30,
        )

    # 10. Timeline Events
    def get_timeline_events(self, limit: int = 14, account: str | None = None) -> list[TimelineEvent]:
        """Derive chronological timeline events from actual stored data.

        Event types:
        - 'solved': first accepted submission for a problem
        - 'attempted': first submission for a problem
        - 'learned': first note created on a problem
        - 'imported': problem creation event (when a problem was added)

        When ``account`` is provided, only submissions from that source account
        are considered for solved/attempted events.
        """
        events: list[TimelineEvent] = []

        account_filter = f"WHERE source_account = '{account}'" if account is not None else "WHERE source_provider IS NULL"
        query = f"""
            SELECT id, submitted_at, status, problem_id, language
            FROM submissions
            {account_filter}
            ORDER BY submitted_at ASC;
        """
        try:
            rows = self.storage.duckdb_repo.conn.execute(query).fetchall()
        except Exception:
            return []

        # Load problems to get slug/title mappings
        problems = self._get_all_problems()
        scoped = self._scope_problems(problems, account)
        problem_map: dict[str, Problem] = {p.id: p for p in scoped}

        # Track first events for each problem
        first_submission: dict[str, str] = {}  # problem_id -> submission_id
        accepted_seen: dict[str, str] = {}  # problem_id -> submission_id

        for sub_id, submitted_at, status, problem_id, language in rows:
            if problem_id not in problem_map:
                continue

            p = problem_map[problem_id]
            submitted_dt = _ensure_utc(submitted_at)

            # First submission = 'attempted' event
            if problem_id not in first_submission:
                first_submission[problem_id] = sub_id
                status_str = str(status) if not hasattr(status, "value") else status.value
                events.append(
                    TimelineEvent(
                        id=f"sub_{sub_id}",
                        kind="attempted",
                        title=f"Attempted {p.title}",
                        detail=f"Started work on {p.title} ({status_str})",
                        problem_id=problem_id,
                        problem_slug=p.slug,
                        language=language,
                        occurred_at=submitted_dt,
                    )
                )

            # First accepted = 'solved' event
            status_str = str(status) if not hasattr(status, "value") else status.value
            if status_str == SubmissionStatus.ACCEPTED.value and problem_id not in accepted_seen:
                accepted_seen[problem_id] = sub_id
                events.append(
                    TimelineEvent(
                        id=f"solved_{sub_id}",
                        kind="solved",
                        title=f"Solved {p.title}",
                        detail=f"Accepted solution in {language}",
                        problem_id=problem_id,
                        problem_slug=p.slug,
                        language=language,
                        occurred_at=submitted_dt,
                    )
                )

        # Add problem import events (scoped to active account)
        for p in scoped:
            events.append(
                TimelineEvent(
                    id=f"imported_{p.id}",
                    kind="imported",
                    title=f"Added {p.title}",
                    detail="Problem imported into CodeMemory",
                    problem_id=p.id,
                    problem_slug=p.slug,
                    occurred_at=p.created_at,
                )
            )

        # Sort by date (most recent first) and limit
        events.sort(key=lambda e: e.occurred_at, reverse=True)
        return events[:limit]

    # 11. Knowledge Clusters
    def get_knowledge_clusters(self, account: str | None = None) -> list:
        """Build knowledge clusters from topic-based problem groupings.

        Clusters are formed by grouping problems that share the same primary topic.
        Each cluster aggregates mastery based on solved problems within that topic.

        When ``account`` is provided, only problems with submissions from that
        account are included in the clusters.
        """
        from codememory.analytics.analytics_models import KnowledgeCluster
        from codememory.domain.models import Problem

        problems = self._get_all_problems()
        if not problems:
            return []
        problems = self._scope_problems(problems, account)
        if not problems:
            return []

        # Group problems by their topics
        topic_problems: dict[str, list[Problem]] = defaultdict(list)
        for p in problems:
            topics = p.topics if p.topics else ["Uncategorized"]
            for topic in topics:
                clean_topic = topic.strip()
                if clean_topic:
                    topic_problems[clean_topic].append(p)

        clusters: list[KnowledgeCluster] = []
        for topic_name in sorted(topic_problems.keys()):
            topic_problems_list = topic_problems[topic_name]
            solved = sum(1 for p in topic_problems_list if p.latest_accepted_submission is not None)
            total = len(topic_problems_list)
            mastery = int((solved / total * 100)) if total > 0 else 0

            clusters.append(
                KnowledgeCluster(
                    id=f"cluster_{topic_name.lower().replace(' ', '_').replace('+', 'and')}",
                    title=topic_name,
                    description=f"{solved}/{total} problems solved",
                    topic_id=topic_name,
                    problem_ids=[p.id for p in topic_problems_list],
                    mastery_pct=mastery,
                )
            )

        return clusters
