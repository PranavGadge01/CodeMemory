"""Comprehensive AnalyticsService using DuckDB and Polars."""

from collections import defaultdict
from datetime import datetime, timezone
from typing import Sequence

import polars as pl

from codememory.analytics.analytics_models import (
    AnalyticsOverview,
    AttemptStat,
    DifficultyStat,
    LanguageStat,
    ProgressOverTime,
    StruggleProblem,
    TopicStat,
)
from codememory.domain.enums import SubmissionStatus
from codememory.domain.models import Problem
from codememory.storage.composite_repository import CompositeStorage


class AnalyticsService:
    """Analytical query engine calculating structured metrics over CodeMemory storage."""

    def __init__(self, storage: CompositeStorage):
        self.storage = storage

    def _get_all_problems(self) -> Sequence[Problem]:
        """Fetch all problems from storage."""
        return self.storage.list_all()

    # 1. System Overview Statistics
    def get_overview(self) -> AnalyticsOverview:
        """Calculate complete system overview statistics."""
        problems = self._get_all_problems()
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
    def get_topic_statistics(self) -> list[TopicStat]:
        """Calculate problem solving metrics grouped by DSA topic."""
        problems = self._get_all_problems()
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
    def get_difficulty_statistics(self) -> list[DifficultyStat]:
        """Calculate problem solving metrics grouped by difficulty."""
        problems = self._get_all_problems()
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
    def get_language_statistics(self) -> list[LanguageStat]:
        """Calculate submission statistics grouped by programming language using DuckDB."""
        try:
            query = """
                SELECT
                    language,
                    COUNT(id) as total_subs,
                    SUM(CASE WHEN status = 'Accepted' THEN 1 ELSE 0 END) as accepted_subs
                FROM submissions
                GROUP BY language
                ORDER BY total_subs DESC;
            """
            rows = self.storage.duckdb_repo.conn.execute(query).fetchall()
        except Exception:
            rows = []

        total_all_subs = sum(r[1] for r in rows) if rows else 0
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
    def get_attempt_statistics(self) -> AttemptStat:
        """Calculate statistics on attempt counts and brute-force->optimized progressions."""
        problems = self._get_all_problems()
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
    def get_progress_over_time(self, granularity: str = "day") -> list[ProgressOverTime]:
        """Aggragate solved problems and submission counts over time using Polars."""
        problems = self._get_all_problems()
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
    def get_struggle_problems(self, limit: int = 10) -> list[StruggleProblem]:
        """Identify problems with high failure rates or multiple failed attempts."""
        problems = self._get_all_problems()
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
