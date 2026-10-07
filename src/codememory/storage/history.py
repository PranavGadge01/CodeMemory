"""Request-scoped read-only snapshot of the user's practice history.

Building the full problem/attempt/submission graph is the single most
expensive read in CodeMemory. Several services (analytics, revision,
evidence, learning) each need overlapping slices of that same graph, and
without a shared representation every one of them re-expands the whole
history from DuckDB.

``HistorySnapshot`` is a plain in-memory view built *once* per logical
operation (an API request, or a single service call that fans out across
history) and passed down to those services. It deliberately holds no
global state, no locks, and no TTL: it lives only for the duration of the
operation that created it, so it cannot leak across requests, accounts, or
concurrent callers.

The snapshot is a read-only projection. Consumers must not mutate the
``Problem``/``Attempt``/``Submission`` objects it exposes; the domain graph
is shared, not deep-copied, so any mutation would be visible to every other
reader in the same operation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

from codememory.domain.models import Attempt, Problem, Submission


@dataclass(frozen=True)
class HistorySnapshot:
    """Immutable index over a single expansion of the practice history."""

    problems: tuple[Problem, ...] = ()
    problems_by_id: Mapping[str, Problem] = field(default_factory=dict)
    problems_by_slug: Mapping[str, Problem] = field(default_factory=dict)
    attempts_by_problem_id: Mapping[str, tuple[Attempt, ...]] = field(default_factory=dict)
    submissions_by_attempt_id: Mapping[str, tuple[Submission, ...]] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def from_problems(cls, problems: Iterable[Problem]) -> "HistorySnapshot":
        """Index an already-loaded sequence of problems."""
        problem_tuple = tuple(problems)

        by_id: dict[str, Problem] = {}
        by_slug: dict[str, Problem] = {}
        attempts_by_problem: dict[str, tuple[Attempt, ...]] = {}
        submissions_by_attempt: dict[str, tuple[Submission, ...]] = {}

        for problem in problem_tuple:
            by_id[problem.id] = problem
            if problem.slug:
                by_slug[problem.slug] = problem

            attempts = tuple(problem.attempts)
            attempts_by_problem[problem.id] = attempts
            for attempt in attempts:
                submissions_by_attempt[attempt.id] = tuple(attempt.submissions)

        return cls(
            problems=problem_tuple,
            problems_by_id=by_id,
            problems_by_slug=by_slug,
            attempts_by_problem_id=attempts_by_problem,
            submissions_by_attempt_id=submissions_by_attempt,
        )

    @classmethod
    def from_storage(cls, storage) -> "HistorySnapshot":
        """Expand storage exactly once and index the result."""
        return cls.from_problems(storage.list_all())

    # ------------------------------------------------------------------
    # Lookups (mirror the storage repository's resolution semantics)
    # ------------------------------------------------------------------

    @property
    def is_empty(self) -> bool:
        return not self.problems

    def get_problem_by_id(self, problem_id: str) -> Problem | None:
        return self.problems_by_id.get(problem_id)

    def get_problem_by_slug(self, slug: str) -> Problem | None:
        return self.problems_by_slug.get(slug)

    def resolve_problem(self, identifier: str) -> Problem | None:
        """Resolve by slug first, then id (matching ``storage.get_by_slug``/``get_by_id``)."""
        return self.problems_by_slug.get(identifier) or self.problems_by_id.get(identifier)

    def attempts_for_problem(self, problem_id: str) -> tuple[Attempt, ...]:
        return self.attempts_by_problem_id.get(problem_id, ())

    def submissions_for_attempt(self, attempt_id: str) -> tuple[Submission, ...]:
        return self.submissions_by_attempt_id.get(attempt_id, ())

    def submissions_for_problem(self, problem_id: str) -> list[Submission]:
        """Flatten a problem's submissions, ordered by submission time.

        Matches ``DuckDBRepository.list_by_problem`` which flattens attempts in
        order and sorts the combined list by ``submitted_at``.
        """
        subs: list[Submission] = []
        for attempt in self.attempts_for_problem(problem_id):
            subs.extend(attempt.submissions)
        return sorted(subs, key=lambda s: s.submitted_at)
