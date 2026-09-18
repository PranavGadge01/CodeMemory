from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import polars as pl

from codememory.domain.enums import DifficultyLevel, SubmissionStatus
from codememory.domain.models import Attempt, Problem, Submission
from codememory.storage.base import AttemptRepository, ProblemRepository, SubmissionRepository


def _clean_dt(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=None)


def _ensure_tz(dt: Any) -> datetime:
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    return datetime.now(timezone.utc)


class ParquetStorage(ProblemRepository, SubmissionRepository, AttemptRepository):
    """Parquet columnar storage repository using Polars."""

    def __init__(self, data_dir: str | Path = "data/parquet"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.problems_path = self.data_dir / "problems.parquet"
        self.attempts_path = self.data_dir / "attempts.parquet"
        self.submissions_path = self.data_dir / "submissions.parquet"

    def health(self) -> bool:
        """Parquet tier is healthy when its data directory is usable."""
        return self.data_dir.is_dir()

    def sync_all(self, problems: Sequence[Problem]) -> None:
        """Overwrite Parquet tables with latest complete domain problem records."""
        prob_rows: list[dict] = []
        att_rows: list[dict] = []
        sub_rows: list[dict] = []

        for p in problems:
            prob_rows.append(
                {
                    "id": str(p.id),
                    "title": str(p.title),
                    "slug": str(p.slug),
                    "difficulty": str(p.difficulty.value if hasattr(p.difficulty, 'value') else p.difficulty),
                    "platform": str(p.platform.value if hasattr(p.platform, 'value') else p.platform),
                    "url": str(p.url or ""),
                    "topics": ", ".join(p.topics) if p.topics else "",
                    "statement": str(p.statement or ""),
                    "created_at": _clean_dt(p.created_at),
                    "updated_at": _clean_dt(p.updated_at),
                }
            )

            for a in p.attempts:
                att_rows.append(
                    {
                        "id": str(a.id),
                        "problem_id": str(a.problem_id),
                        "attempt_number": int(a.attempt_number),
                        "approach_summary": str(a.approach_summary or ""),
                        "reasoning": str(a.reasoning or ""),
                        "status": str(a.status.value if hasattr(a.status, 'value') else a.status),
                        "time_complexity": a.analysis.time_complexity if a.analysis else "",
                        "space_complexity": a.analysis.space_complexity if a.analysis else "",
                        "created_at": _clean_dt(a.created_at),
                        "updated_at": _clean_dt(a.updated_at),
                    }
                )

                for s in a.submissions:
                    sub_rows.append(
                        {
                            "id": str(s.id),
                            "problem_id": str(s.problem_id),
                            "attempt_id": str(s.attempt_id or a.id),
                            "code": str(s.code or ""),
                            "language": str(s.language or ""),
                            "status": str(s.status.value if hasattr(s.status, 'value') else s.status),
                            "runtime_ms": float(s.runtime_ms) if s.runtime_ms is not None else None,
                            "memory_mb": float(s.memory_mb) if s.memory_mb is not None else None,
                            "submitted_at": _clean_dt(s.submitted_at),
                            "error_message": str(s.error_message or ""),
                            "submission_hash": str(s.submission_hash or ""),
                        }
                    )

        if prob_rows:
            pl.DataFrame(prob_rows).write_parquet(self.problems_path)
        elif self.problems_path.exists():
            self.problems_path.unlink()

        if att_rows:
            pl.DataFrame(att_rows).write_parquet(self.attempts_path)
        elif self.attempts_path.exists():
            self.attempts_path.unlink()

        if sub_rows:
            pl.DataFrame(sub_rows).write_parquet(self.submissions_path)
        elif self.submissions_path.exists():
            self.submissions_path.unlink()

    def save(self, problem: Problem) -> Problem:
        """Save a single problem by reading existing Parquet state, updating, and syncing."""
        problems = list(self.list_all())
        updated = False
        for i, p in enumerate(problems):
            if p.id == problem.id or p.slug == problem.slug:
                problems[i] = problem
                updated = True
                break
        if not updated:
            problems.append(problem)
        self.sync_all(problems)
        return problem

    def get_by_id(self, problem_id: str) -> Problem | None:
        all_p = self.list_all()
        for p in all_p:
            if p.id == problem_id:
                return p
        return None

    def get_by_slug(self, slug: str) -> Problem | None:
        all_p = self.list_all()
        for p in all_p:
            if p.slug == slug:
                return p
        return None

    def list_all(self) -> Sequence[Problem]:
        if not self.problems_path.exists():
            return []

        df_p = pl.read_parquet(self.problems_path)
        df_a = pl.read_parquet(self.attempts_path) if self.attempts_path.exists() else pl.DataFrame()
        df_s = pl.read_parquet(self.submissions_path) if self.submissions_path.exists() else pl.DataFrame()

        problems: list[Problem] = []
        for p_row in df_p.iter_rows(named=True):
            pid = p_row["id"]
            # match attempts
            p_attempts: list[Attempt] = []
            if not df_a.is_empty():
                sub_df_a = df_a.filter(pl.col("problem_id") == pid)
                for a_row in sub_df_a.iter_rows(named=True):
                    aid = a_row["id"]
                    # match submissions
                    a_subs: list[Submission] = []
                    if not df_s.is_empty():
                        sub_df_s = df_s.filter(pl.col("attempt_id") == aid)
                        for s_row in sub_df_s.iter_rows(named=True):
                            sub = Submission(
                                id=s_row["id"],
                                problem_id=s_row["problem_id"],
                                attempt_id=s_row["attempt_id"],
                                code=s_row["code"],
                                language=s_row["language"],
                                status=SubmissionStatus.parse(s_row["status"]),
                                runtime_ms=s_row["runtime_ms"],
                                memory_mb=s_row["memory_mb"],
                                submitted_at=_ensure_tz(s_row["submitted_at"]),
                                error_message=s_row["error_message"] or None,
                                submission_hash=s_row["submission_hash"],
                            )
                            a_subs.append(sub)

                    att = Attempt(
                        id=a_row["id"],
                        problem_id=a_row["problem_id"],
                        attempt_number=a_row["attempt_number"],
                        approach_summary=a_row["approach_summary"],
                        reasoning=a_row["reasoning"] or None,
                        status=SubmissionStatus.parse(a_row["status"]),
                        created_at=_ensure_tz(a_row["created_at"]),
                        updated_at=_ensure_tz(a_row["updated_at"]),
                        submissions=a_subs,
                    )
                    p_attempts.append(att)

            topics_list = [t.strip() for t in p_row["topics"].split(",") if t.strip()] if p_row.get("topics") else []
            prob = Problem(
                id=p_row["id"],
                title=p_row["title"],
                slug=p_row["slug"],
                difficulty=DifficultyLevel.parse(p_row["difficulty"]),
                platform=p_row["platform"],
                url=p_row["url"] or None,
                topics=topics_list,
                statement=p_row["statement"] or None,
                created_at=_ensure_tz(p_row["created_at"]),
                updated_at=_ensure_tz(p_row["updated_at"]),
                attempts=p_attempts,
            )
            problems.append(prob)

        return problems

    def delete(self, problem_id: str) -> bool:
        all_p = [p for p in self.list_all() if p.id != problem_id]
        self.sync_all(all_p)
        return True

    def save_submission(self, submission: Submission) -> Submission:
        probs = list(self.list_all())
        for p in probs:
            if p.id == submission.problem_id or p.slug == submission.problem_id:
                if not p.attempts:
                    p.attempts.append(Attempt(problem_id=p.id, attempt_number=1, status=submission.status))
                p.attempts[-1].submissions.append(submission)
                break
        self.sync_all(probs)
        return submission

    def get_by_hash(self, submission_hash: str) -> Submission | None:
        if not self.submissions_path.exists():
            return None
        df_s = pl.read_parquet(self.submissions_path)
        filtered = df_s.filter(pl.col("submission_hash") == submission_hash)
        if filtered.is_empty():
            return None
        row = filtered.to_dicts()[0]
        return Submission(
            id=row["id"],
            problem_id=row["problem_id"],
            attempt_id=row["attempt_id"],
            code=row["code"],
            language=row["language"],
            status=SubmissionStatus.parse(row["status"]),
            runtime_ms=row["runtime_ms"],
            memory_mb=row["memory_mb"],
            submitted_at=_ensure_tz(row["submitted_at"]),
            error_message=row["error_message"] or None,
            submission_hash=row["submission_hash"],
        )

    def list_by_problem(self, problem_id: str) -> Sequence[Submission]:
        prob = self.get_by_id(problem_id) or self.get_by_slug(problem_id)
        if not prob:
            return []
        subs: list[Submission] = []
        for a in prob.attempts:
            subs.extend(a.submissions)
        return subs

    def list_by_attempt(self, attempt_id: str) -> Sequence[Submission]:
        probs = self.list_all()
        for p in probs:
            for a in p.attempts:
                if a.id == attempt_id:
                    return a.submissions
        return []

    def save_attempt(self, attempt: Attempt) -> Attempt:
        probs = list(self.list_all())
        for p in probs:
            if p.id == attempt.problem_id:
                for i, a in enumerate(p.attempts):
                    if a.id == attempt.id:
                        p.attempts[i] = attempt
                        break
                else:
                    p.attempts.append(attempt)
                break
        self.sync_all(probs)
        return attempt
