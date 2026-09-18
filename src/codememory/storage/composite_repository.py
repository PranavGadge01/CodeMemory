"""Composite repository orchestrating Filesystem, Parquet, and DuckDB storage tiers."""

from pathlib import Path
from typing import Sequence

from codememory.domain.models import Attempt, Problem, Submission
from codememory.storage.base import AttemptRepository, ProblemRepository, SubmissionRepository
from codememory.storage.duckdb_repository import DuckDBStorage
from codememory.storage.fs_repository import FilesystemStorage
from codememory.storage.parquet_repository import ParquetStorage


class CompositeStorage(ProblemRepository, SubmissionRepository, AttemptRepository):
    """Unified storage coordinator maintaining parity across Markdown, Parquet, and DuckDB."""

    def __init__(
        self,
        base_dir: str | Path = "data",
        knowledge_dir: str | Path = "knowledge",
        db_path: str | Path = "data/codememory.duckdb",
    ):
        self.base_dir = Path(base_dir)
        self.fs_repo = FilesystemStorage(root_dir=knowledge_dir)
        self.parquet_repo = ParquetStorage(data_dir=self.base_dir / "parquet")
        self.duckdb_repo = DuckDBStorage(db_path=db_path)

    def save(self, problem: Problem) -> Problem:
        """Atomically persist problem across DuckDB, Parquet, and Filesystem."""
        # 1. Save in DuckDB
        prob = self.duckdb_repo.save(problem)
        # 2. Save in Filesystem / Markdown
        self.fs_repo.save(prob)
        # 3. Sync Parquet datasets
        all_problems = self.duckdb_repo.list_all()
        self.parquet_repo.sync_all(all_problems)
        return prob

    def get_by_id(self, problem_id: str) -> Problem | None:
        """Get problem from fast DuckDB index (fallback to FS)."""
        prob = self.duckdb_repo.get_by_id(problem_id)
        if not prob:
            prob = self.fs_repo.get_by_id(problem_id)
        return prob

    def get_by_slug(self, slug: str) -> Problem | None:
        """Get problem by slug."""
        prob = self.duckdb_repo.get_by_slug(slug)
        if not prob:
            prob = self.fs_repo.get_by_slug(slug)
        return prob

    def list_all(self) -> Sequence[Problem]:
        """List all problems from DuckDB storage."""
        return self.duckdb_repo.list_all()

    def health(self) -> bool:
        """Return True only when every coordinated storage tier is healthy."""
        return all(self.tier_health().values())

    def tier_health(self) -> dict[str, bool]:
        """Return the health of each coordinated storage tier."""
        return {
            "duckdb": self.duckdb_repo.health(),
            "parquet": self.parquet_repo.health(),
            "filesystem": self.fs_repo.health(),
        }

    def delete(self, problem_id: str) -> bool:
        """Delete problem from all storage tiers."""
        prob = self.get_by_id(problem_id)
        if not prob:
            return False
        self.fs_repo.delete(problem_id)
        self.duckdb_repo.delete(problem_id)
        all_problems = self.duckdb_repo.list_all()
        self.parquet_repo.sync_all(all_problems)
        return True

    def save_submission(self, submission: Submission) -> Submission:
        """Save submission and update all storage tiers."""
        prob = self.get_by_id(submission.problem_id) or self.get_by_slug(submission.problem_id)
        if prob:
            # find or create attempt
            matched_attempt = None
            if submission.attempt_id:
                for a in prob.attempts:
                    if a.id == submission.attempt_id:
                        matched_attempt = a
                        break
            if not matched_attempt:
                if prob.attempts:
                    matched_attempt = prob.attempts[-1]
                else:
                    matched_attempt = Attempt(
                        problem_id=prob.id,
                        attempt_number=1,
                        status=submission.status,
                    )
                    prob.attempts.append(matched_attempt)

            # verify idempotency hash
            existing_hashes = {s.submission_hash for s in matched_attempt.submissions if s.submission_hash}
            if submission.submission_hash not in existing_hashes:
                submission.attempt_id = matched_attempt.id
                matched_attempt.submissions.append(submission)
                self.save(prob)
        return submission

    def get_by_hash(self, submission_hash: str) -> Submission | None:
        """Check idempotency hash across DuckDB repository."""
        return self.duckdb_repo.get_by_hash(submission_hash)

    def list_by_problem(self, problem_id: str) -> Sequence[Submission]:
        return self.duckdb_repo.list_by_problem(problem_id)

    def list_by_attempt(self, attempt_id: str) -> Sequence[Submission]:
        return self.duckdb_repo.list_by_attempt(attempt_id)

    def save_attempt(self, attempt: Attempt) -> Attempt:
        prob = self.get_by_id(attempt.problem_id)
        if prob:
            for i, a in enumerate(prob.attempts):
                if a.id == attempt.id:
                    prob.attempts[i] = attempt
                    break
            else:
                prob.attempts.append(attempt)
            self.save(prob)
        return attempt

    def export_all_knowledge(self) -> None:
        """Trigger re-export of all problems to knowledge filesystem."""
        problems = self.list_all()
        for p in problems:
            self.fs_repo.save(p)
