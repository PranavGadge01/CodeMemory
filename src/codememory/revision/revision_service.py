"""Deterministic Revision Service for CodeMemory."""

from datetime import datetime, timezone
from typing import Sequence

from codememory.analytics.analytics_service import AnalyticsService
from codememory.domain.enums import DifficultyLevel, NoteType, SubmissionStatus
from codememory.domain.models import Problem
from codememory.revision.revision_models import (
    RevisionQueueItem,
    RevisionScoreBreakdown,
    RevisionWeights,
)
from codememory.storage.composite_repository import CompositeStorage


class RevisionService:
    """Revision engine calculating problem priority queues and tracking reviews."""

    def __init__(self, storage: CompositeStorage, analytics_service: AnalyticsService | None = None):
        self.storage = storage
        self.analytics = analytics_service or AnalyticsService(storage=storage)

    def get_problem_priority(
        self,
        problem_identifier: str,
        weights: RevisionWeights | None = None,
    ) -> RevisionScoreBreakdown:
        """Calculate detailed revision priority score for a problem."""
        w = weights or RevisionWeights()
        prob = self.storage.get_by_slug(problem_identifier) or self.storage.get_by_id(problem_identifier)

        if not prob:
            raise ValueError(f"Problem not found: '{problem_identifier}'")

        now = datetime.now(timezone.utc)

        # 1. Difficulty score
        diff_map = {
            DifficultyLevel.EASY: 1.0,
            DifficultyLevel.MEDIUM: 2.0,
            DifficultyLevel.HARD: 3.0,
            DifficultyLevel.UNKNOWN: 0.5,
        }
        diff_score = diff_map.get(prob.difficulty, 1.0)

        # 2. Failure score (failed attempts / submissions)
        failed_attempts_count = sum(1 for a in prob.attempts if not a.is_accepted)
        failed_subs_count = sum(1 for a in prob.attempts for s in a.submissions if s.status != SubmissionStatus.ACCEPTED)
        fail_score = min(float(max(failed_attempts_count, failed_subs_count)), 5.0)

        # 3. Recency score (days since last activity/attempt/note)
        def _to_utc(dt: datetime) -> datetime:
            return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt

        last_dt = _to_utc(prob.updated_at)
        for a in prob.attempts:
            a_dt = _to_utc(a.updated_at)
            if a_dt > last_dt:
                last_dt = a_dt
            for s in a.submissions:
                s_dt = _to_utc(s.submitted_at)
                if s_dt > last_dt:
                    last_dt = s_dt
        for n in prob.notes:
            n_dt = _to_utc(n.created_at)
            if n_dt > last_dt:
                last_dt = n_dt

        days_since = max((now - last_dt).days, 0)
        recency_score = min(days_since / 7.0, 10.0)

        # 4. Weakness score (belongs to a weak topic)
        weak_topics = {wt.topic for wt in self.analytics.get_topic_statistics() if wt.success_rate_pct < 50.0}
        prob_topics = {t.strip() for t in prob.topics}
        weakness_score = 2.0 if any(t in weak_topics for t in prob_topics) else 0.0

        # 5. Recent solved penalty
        recent_solved_penalty = 0.0
        if prob.latest_accepted_submission:
            if days_since <= 3:
                recent_solved_penalty = (4.0 - days_since)  # Penalty for very recently solved

        # Calculate final score
        final_score = (
            (w.difficulty_weight * diff_score)
            + (w.failure_weight * fail_score)
            + (w.recency_weight * recency_score)
            + (w.weakness_weight * weakness_score)
            - (w.recent_solved_penalty_weight * recent_solved_penalty)
        )

        return RevisionScoreBreakdown(
            problem_id=prob.id,
            title=prob.title,
            slug=prob.slug,
            difficulty=prob.difficulty.value,
            final_score=round(final_score, 2),
            difficulty_score=diff_score,
            failure_score=fail_score,
            recency_score=round(recency_score, 2),
            weakness_score=weakness_score,
            recent_solved_penalty=round(recent_solved_penalty, 2),
            days_since_last_activity=days_since,
        )

    def get_revision_queue(
        self,
        limit: int = 10,
        topic: str | None = None,
        weights: RevisionWeights | None = None,
    ) -> list[RevisionQueueItem]:
        """Generate prioritized revision queue ordered by score descending."""
        problems = self.storage.list_all()
        queue: list[RevisionQueueItem] = []

        if topic and topic.strip():
            t_lower = topic.strip().lower()
            problems = [p for p in problems if any(t_lower in pt.lower() for pt in p.topics)]

        for p in problems:
            bd = self.get_problem_priority(p.id, weights=weights)

            # Get latest activity timestamp
            last_dt = p.updated_at
            for a in p.attempts:
                if a.updated_at > last_dt:
                    last_dt = a.updated_at
            for n in p.notes:
                if n.created_at > last_dt:
                    last_dt = n.created_at

            queue.append(
                RevisionQueueItem(
                    problem_id=p.id,
                    title=p.title,
                    slug=p.slug,
                    difficulty=p.difficulty.value,
                    priority_score=bd.final_score,
                    last_activity_at=last_dt,
                    topics=p.topics,
                    breakdown=bd,
                )
            )

        queue.sort(key=lambda item: item.priority_score, reverse=True)
        return queue[:limit]

    def get_due_problems(self, threshold_days: int = 7, limit: int = 10) -> list[RevisionQueueItem]:
        """Fetch problems that have not been attempted or reviewed in threshold_days."""
        full_queue = self.get_revision_queue(limit=100)
        due = [item for item in full_queue if item.breakdown.days_since_last_activity >= threshold_days]
        return due[:limit]

    def mark_reviewed(self, problem_identifier: str, notes: str | None = None) -> Problem:
        """Mark a problem as reviewed by adding a review note and updating timestamp."""
        prob = self.storage.get_by_slug(problem_identifier) or self.storage.get_by_id(problem_identifier)
        if not prob:
            raise ValueError(f"Problem not found: '{problem_identifier}'")

        now = datetime.now(timezone.utc)
        prob.updated_at = now

        note_content = notes or "Marked problem as reviewed in revision cycle."
        self.storage.save(prob)

        # Attach note via storage repository
        from codememory.domain.models import ProblemNote
        pnote = ProblemNote(
            problem_id=prob.id,
            content=note_content,
            note_type=NoteType.GENERAL,
            created_at=now,
        )
        prob.notes.append(pnote)
        self.storage.save(prob)
        return prob
