"""Tests for the deterministic per-submission learning analysis."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from codememory.core.service import CodeMemoryService
from codememory.domain.enums import DifficultyLevel, SubmissionStatus
from codememory.domain.models import Attempt, Problem, Submission
from codememory.learning.submission_insight import build_submission_learning_analysis

BASE_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)

NESTED_CODE = "for i in range(len(nums)):\n    for j in range(len(nums)):\n        if nums[i] + nums[j] == target:\n            return [i, j]\nreturn []"
HASH_CODE = "seen = {}\nfor i, n in enumerate(nums):\n    if target - n in seen:\n        return [seen[target - n], i]\n    seen[n] = i\nreturn []"


def make_problem(slug="two-sum", topics=("Array", "Hash Table"), difficulty=DifficultyLevel.EASY):
    return Problem(
        id=slug, title=slug.replace("-", " ").title(), slug=slug,
        difficulty=difficulty, platform="LeetCode", topics=list(topics),
    )


def make_submission(problem, code=HASH_CODE, status=SubmissionStatus.ACCEPTED, *, sid=None,
                    runtime_ms=None, memory_mb=None, day=0):
    return Submission(
        id=sid or f"sub-{problem.slug}-{day}",
        problem_id=problem.id,
        code=code,
        language="python",
        status=status,
        runtime_ms=runtime_ms,
        memory_mb=memory_mb,
        submitted_at=BASE_TIME + timedelta(days=day),
    )


def build(problem, submission, previous=None, **kwargs):
    return build_submission_learning_analysis(problem, submission, previous_submission=previous, **kwargs)


# ─── Accepted / failed ───────────────────────────────────────────────────────

class TestAcceptedSubmission:
    def test_overview_and_strengths(self):
        problem = make_problem()
        result = build(problem, make_submission(problem))
        assert result.status == "Accepted"
        assert "Accepted" in result.overview
        assert result.what_went_well
        assert result.has_code is True

    def test_lesson_and_next_action_present(self):
        problem = make_problem()
        result = build(problem, make_submission(problem))
        assert result.lesson
        assert result.next_action

    def test_edge_cases_are_topic_specific(self):
        problem = make_problem()
        result = build(problem, make_submission(problem))
        assert result.edge_cases


class TestFailedSubmission:
    def test_correctness_improvement_is_raised(self):
        problem = make_problem()
        sub = make_submission(problem, code=NESTED_CODE, status=SubmissionStatus.WRONG_ANSWER)
        result = build(problem, sub)
        titles = " ".join(i.title for i in result.improvements)
        assert "correctness" in titles.lower()
        assert result.status == "Wrong Answer"

    def test_tle_explains_complexity(self):
        problem = make_problem()
        sub = make_submission(problem, code=NESTED_CODE, status=SubmissionStatus.TIME_LIMIT_EXCEEDED)
        result = build(problem, sub)
        assert result.current_time_complexity == "O(n²)"
        assert any("Reduce time" in i.title for i in result.improvements)


# ─── Comparison ──────────────────────────────────────────────────────────────

class TestPreviousAttemptComparison:
    def test_no_previous_is_honest(self):
        problem = make_problem()
        result = build(problem, make_submission(problem))
        assert result.previous_attempt_comparison.available is False
        assert "No earlier" in result.previous_attempt_comparison.summary

    def test_previous_without_code_is_honest(self):
        problem = make_problem()
        prev = make_submission(problem, code="", status=SubmissionStatus.WRONG_ANSWER, day=0)
        cur = make_submission(problem, code=HASH_CODE, day=1)
        result = build(problem, cur, previous=prev)
        assert result.previous_attempt_comparison.available is False
        assert "No earlier source submission is available" in result.previous_attempt_comparison.summary

    def test_nested_to_linear_is_detected(self):
        problem = make_problem()
        prev = make_submission(problem, code=NESTED_CODE, status=SubmissionStatus.TIME_LIMIT_EXCEEDED, day=0)
        cur = make_submission(problem, code=HASH_CODE, status=SubmissionStatus.ACCEPTED, day=1)
        result = build(problem, cur, previous=prev)
        cmp = result.previous_attempt_comparison
        assert cmp.available is True
        assert any("Nested iteration" in c for c in cmp.changes)
        assert "Resolved" in cmp.improvement

    def test_runtime_and_memory_deltas(self):
        problem = make_problem()
        code = "nums.sort()\nreturn nums"
        prev = make_submission(problem, code=code, status=SubmissionStatus.WRONG_ANSWER, day=0, runtime_ms=120.0, memory_mb=20.0)
        cur = make_submission(problem, code=code, status=SubmissionStatus.ACCEPTED, day=1, runtime_ms=50.0, memory_mb=15.0)
        result = build(problem, cur, previous=prev)
        summary = result.previous_attempt_comparison.summary
        assert "Runtime" in summary
        assert "Memory" in summary


# ─── Missing code ────────────────────────────────────────────────────────────

class TestMissingSource:
    def test_missing_code_is_honest(self):
        problem = make_problem()
        sub = make_submission(problem, code="")
        result = build(problem, sub)
        assert result.has_code is False
        assert result.current_time_complexity == "Unknown"
        assert result.complexity_source == "unavailable"
        assert any("No source code" in lim for lim in result.limitations)

    def test_code_estimate_is_labeled(self):
        problem = make_problem()
        result = build(problem, make_submission(problem, code=HASH_CODE))
        assert result.complexity_source == "code_estimate"


# ─── Optimization & cross-problem ────────────────────────────────────────────

class TestOptimizationAndConnections:
    def test_alternative_approach_and_tradeoffs(self):
        problem = make_problem()
        sub = make_submission(problem, code=NESTED_CODE, status=SubmissionStatus.TIME_LIMIT_EXCEEDED)
        result = build(problem, sub)
        assert result.alternative_approach
        assert result.tradeoffs
        assert result.general_pattern

    def test_cross_problem_connection_uses_history(self):
        problem = make_problem(slug="two-sum")
        history = {"HashMap / Dictionary": ["Two Sum", "Group Anagrams"]}
        result = build(problem, make_submission(problem), pattern_history=history)
        assert result.cross_problem_connections

    def test_no_connection_without_history(self):
        problem = make_problem()
        result = build(problem, make_submission(problem))
        assert result.cross_problem_connections == []


# ─── Service integration ─────────────────────────────────────────────────────

@pytest.fixture()
def service():
    svc = CodeMemoryService(db_path=":memory:")
    yield svc
    svc.close_storage()


class TestServiceIntegration:
    def _seed(self, svc):
        problem = make_problem()
        prev = make_submission(problem, code=NESTED_CODE, status=SubmissionStatus.TIME_LIMIT_EXCEEDED, day=0, sid="prev-1")
        cur = make_submission(problem, code=HASH_CODE, status=SubmissionStatus.ACCEPTED, day=1, sid="cur-1")
        problem.attempts.append(Attempt(problem_id=problem.id, attempt_number=1, status=prev.status, submissions=[prev]))
        problem.attempts.append(Attempt(problem_id=problem.id, attempt_number=2, status=cur.status, submissions=[cur]))
        svc.storage.save(problem)
        return problem

    def test_service_returns_comparison(self, service):
        self._seed(service)
        result = service.get_submission_learning_analysis("cur-1")
        assert result.previous_attempt_comparison.available is True
        assert result.previous_attempt_comparison.previous_submission_id == "prev-1"

    def test_service_raises_for_unknown(self, service):
        with pytest.raises(ValueError):
            service.get_submission_learning_analysis("nope")

    def test_service_uses_cached_analysis_when_present(self, service):
        self._seed(service)
        service.analyze_submission("cur-1")
        result = service.get_submission_learning_analysis("cur-1")
        assert result.complexity_source in {"code_analysis", "attempt_analysis"}
