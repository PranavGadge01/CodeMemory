"""Tests for the deterministic collective learning insight engine.

Covers aggregate statistics, strengths, weaknesses vs unpracticed areas,
recurring mistakes, optimization trends, difficulty/topic progression,
early-vs-recent comparison, prioritisation, sparse history and evidence refs.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from codememory.core.service import CodeMemoryService
from codememory.domain.enums import DifficultyLevel, SubmissionStatus
from codememory.domain.models import Attempt, Problem, Submission
from codememory.learning.collective import build_collective_learning_insight

BASE_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)

NESTED_CODE = "total = 0\nfor i in range(len(nums)):\n    for j in range(len(nums)):\n        if nums[i] + nums[j] == target:\n            total += 1\nreturn total"
HASH_CODE = "seen = {}\nfor i, n in enumerate(nums):\n    if target - n in seen:\n        return [seen[target - n], i]\n    seen[n] = i\nreturn []"
SORT_CODE = "nums.sort()\nleft, right = 0, len(nums) - 1\nwhile left < right:\n    total = nums[left] + nums[right]\n    if total == target:\n        return [left, right]\n    left += 1\nreturn []"


@pytest.fixture()
def service():
    svc = CodeMemoryService(db_path=":memory:")
    yield svc
    svc.close_storage()


def seed_problem(svc, slug, topics, difficulty, attempts, *, day=0, base=BASE_TIME):
    problem = Problem(
        id=slug,
        title=slug.replace("-", " ").title(),
        slug=slug,
        difficulty=difficulty,
        platform="LeetCode",
        topics=list(topics),
    )
    for index, spec in enumerate(attempts):
        status = spec["status"]
        problem.attempts.append(
            Attempt(
                problem_id=problem.id,
                attempt_number=index + 1,
                status=status,
                submissions=[
                    Submission(
                        problem_id=problem.id,
                        code=spec.get("code", "pass"),
                        language="python",
                        status=status,
                        runtime_ms=spec.get("runtime_ms"),
                        memory_mb=spec.get("memory_mb"),
                        submitted_at=base + timedelta(days=day, minutes=index),
                    )
                ],
            )
        )
    svc.storage.save(problem)
    return problem


def solved(svc, slug, topics, difficulty=DifficultyLevel.EASY, day=0, code=HASH_CODE):
    return seed_problem(svc, slug, topics, difficulty, [{"status": SubmissionStatus.ACCEPTED, "code": code}], day=day)


def _insight(svc):
    return svc.get_collective_learning_insight()


# ─── Aggregate statistics ────────────────────────────────────────────────────

class TestAggregateStatistics:
    def test_profile_matches_analytics_overview(self, service):
        solved(service, "a-one", ["Array"], day=0)
        solved(service, "a-two", ["Array"], day=1)
        seed_problem(service, "b-one", ["Dynamic Programming"], DifficultyLevel.MEDIUM,
                     [{"status": SubmissionStatus.WRONG_ANSWER, "code": NESTED_CODE}], day=2)
        overview = service.analytics_service.get_overview(account=None)
        profile = _insight(service).profile
        assert profile.total_problems == overview.total_problems
        assert profile.total_solved == overview.accepted_problems
        assert profile.total_submissions == overview.total_submissions
        assert profile.acceptance_rate_pct == round(overview.overall_acceptance_rate_pct, 1)

    def test_language_share_is_computed(self, service):
        solved(service, "a-one", ["Array"], day=0)
        profile = _insight(service).profile
        assert profile.language_share
        assert profile.language_share[0]["language"] == "python"


# ─── Strengths ───────────────────────────────────────────────────────────────

class TestStrengths:
    def test_topic_strength_from_multiple_solves(self, service):
        solved(service, "hw-one", ["Hash Table"], day=0)
        solved(service, "hw-two", ["Hash Table"], day=1)
        strengths = _insight(service).strengths
        titles = " ".join(s.title for s in strengths)
        assert "Hash Table" in titles

    def test_no_strength_claimed_from_single_solve(self, service):
        solved(service, "only-one", ["Array"], day=0)
        assert _insight(service).strengths == []

    def test_difficulty_strength(self, service):
        solved(service, "m-one", ["Array"], DifficultyLevel.MEDIUM, day=0)
        solved(service, "m-two", ["Array"], DifficultyLevel.MEDIUM, day=1)
        titles = " ".join(s.title for s in _insight(service).strengths)
        assert "Progress beyond Easy" in titles


# ─── Weaknesses vs unpracticed ───────────────────────────────────────────────

class TestWeaknessAndGaps:
    def test_struggled_topic_is_a_weakness(self, service):
        seed_problem(service, "dp-one", ["Dynamic Programming"], DifficultyLevel.MEDIUM,
                     [{"status": SubmissionStatus.WRONG_ANSWER, "code": NESTED_CODE}], day=0)
        seed_problem(service, "dp-two", ["Dynamic Programming"], DifficultyLevel.MEDIUM,
                     [{"status": SubmissionStatus.TIME_LIMIT_EXCEEDED, "code": NESTED_CODE}], day=1)
        insight = _insight(service)
        assert any("Dynamic Programming" in w.title for w in insight.weaknesses)

    def test_unpracticed_topic_is_not_a_weakness(self, service):
        solved(service, "a-one", ["Array"], day=0)
        solved(service, "a-two", ["Array"], day=1)
        insight = _insight(service)
        assert not any("Graph" in w.title for w in insight.weaknesses)
        unpracticed_titles = [f.title for f in insight.focus_areas if "not practiced" in f.title]
        assert unpracticed_titles, "unpracticed topics should surface as focus areas"

    def test_unpracticed_items_are_facts_not_interpretations(self, service):
        solved(service, "a-one", ["Array"], day=0)
        insight = _insight(service)
        for item in insight.focus_areas:
            if "not practiced" in item.title:
                assert item.category in {"fact", "action"}
                assert "weakness" in item.impact.lower() or "gap" in item.impact.lower()


# ─── Recurring mistakes ──────────────────────────────────────────────────────

class TestRecurringMistakes:
    def test_repeated_wrong_answers_are_recurring(self, service):
        seed_problem(service, "w-one", ["Array"], DifficultyLevel.EASY,
                     [{"status": SubmissionStatus.WRONG_ANSWER, "code": SORT_CODE}], day=0)
        seed_problem(service, "w-two", ["Array"], DifficultyLevel.EASY,
                     [{"status": SubmissionStatus.WRONG_ANSWER, "code": SORT_CODE}], day=1)
        mistakes = _insight(service).recurring_mistakes
        assert mistakes, "two WA submissions should yield a recurring mistake"
        assert all(m.confidence == "recurring" for m in mistakes)

    def test_single_failure_is_not_recurring(self, service):
        seed_problem(service, "w-one", ["Array"], DifficultyLevel.EASY,
                     [{"status": SubmissionStatus.WRONG_ANSWER, "code": SORT_CODE}], day=0)
        solved(service, "ok-one", ["Array"], day=1)
        mistakes = _insight(service).recurring_mistakes
        assert all(m.summary != "Observed across 1 submission(s)." for m in mistakes)


# ─── Optimization trends ─────────────────────────────────────────────────────

class TestOptimizationTrends:
    def test_nested_to_linear_is_detected(self, service):
        seed_problem(
            service, "opt-one", ["Array"], DifficultyLevel.EASY,
            [
                {"status": SubmissionStatus.TIME_LIMIT_EXCEEDED, "code": NESTED_CODE},
                {"status": SubmissionStatus.ACCEPTED, "code": HASH_CODE, "runtime_ms": 40.0},
            ],
            day=0,
        )
        insight = _insight(service)
        trends = " ".join(t.title for t in insight.optimization_trends)
        assert "optimized" in trends.lower()
        assert any("Optimization is recognized after implementation" in w.title for w in insight.weaknesses)

    def test_flat_complexity_when_no_change(self, service):
        seed_problem(
            service, "flat-one", ["Array"], DifficultyLevel.EASY,
            [
                {"status": SubmissionStatus.ACCEPTED, "code": SORT_CODE},
                {"status": SubmissionStatus.ACCEPTED, "code": SORT_CODE},
            ],
            day=0,
        )
        trends = " ".join(t.title for t in _insight(service).optimization_trends)
        assert "No complexity improvement" in trends

# ─── Progress, prioritisation, sparse data, grounding ────────────────────────

class TestProgress:
    def test_early_vs_recent_requires_enough_data(self, service):
        for i in range(8):
            status = SubmissionStatus.WRONG_ANSWER if i < 4 else SubmissionStatus.ACCEPTED
            seed_problem(service, f"p-{i}", ["Array"], DifficultyLevel.EASY,
                         [{"status": status, "code": HASH_CODE}], day=i)
        progress = _insight(service).progress
        assert progress
        metrics = {p.metric for p in progress}
        assert "Acceptance rate" in metrics

    def test_no_progress_for_tiny_history(self, service):
        solved(service, "a-one", ["Array"], day=0)
        assert _insight(service).progress == []


class TestPrioritisation:
    def test_items_are_sorted_high_first(self, service):
        seed_problem(service, "dp-one", ["Dynamic Programming"], DifficultyLevel.MEDIUM,
                     [{"status": SubmissionStatus.WRONG_ANSWER, "code": NESTED_CODE}], day=0)
        insight = _insight(service)
        order = {"high": 0, "medium": 1, "low": 2}
        for group in (insight.weaknesses, insight.focus_areas):
            ranks = [order[i.priority] for i in group]
            assert ranks == sorted(ranks)

    def test_priorities_are_valid_labels(self, service):
        solved(service, "a-one", ["Array"], day=0)
        solved(service, "a-two", ["Array"], day=1)
        insight = _insight(service)
        for item in insight.strengths + insight.weaknesses + insight.focus_areas + insight.recurring_mistakes:
            assert item.priority in {"high", "medium", "low"}
            assert item.confidence in {"recurring", "early_signal"}


class TestSparseHistory:
    def test_single_problem_is_early_stage(self, service):
        solved(service, "a-one", ["Array"], day=0)
        insight = _insight(service)
        assert insight.is_early_stage is True
        assert insight.limitations

    def test_empty_history_has_no_fabricated_strengths(self, service):
        insight = _insight(service)
        assert insight.strengths == []
        assert insight.weaknesses == []
        assert insight.profile.total_problems == 0

    def test_two_problem_profile_is_cautious(self, service):
        solved(service, "a-one", ["Array"], day=0)
        solved(service, "a-two", ["Array"], day=1)
        insight = _insight(service)
        assert insight.is_early_stage is True
        assert any("preliminary" in lim or "Only 2" in lim for lim in insight.limitations)


class TestEvidenceGrounding:
    def _build(self, svc):
        evidence = svc.evidence_builder.build_full_profile_evidence(account=None)
        problems = svc.analytics_service._scope_problems(
            svc.analytics_service._get_all_problems(), None
        )
        analyses = svc.ai_analyzer.get_cached_analyses()
        insight = build_collective_learning_insight(evidence, problems, analyses)
        return evidence, insight

    def test_all_item_refs_exist_in_evidence(self, service):
        solved(service, "a-one", ["Array"], day=0)
        solved(service, "a-two", ["Array"], day=1)
        problem = seed_problem(service, "w-one", ["Array"], DifficultyLevel.EASY,
                               [{"status": SubmissionStatus.WRONG_ANSWER, "code": NESTED_CODE}], day=2)
        service.analyze_submission(problem.attempts[0].submissions[0].id)
        evidence, insight = self._build(service)
        valid = evidence.all_evidence_ids()
        for item in (
            insight.strengths + insight.weaknesses + insight.focus_areas
            + insight.recurring_mistakes + insight.optimization_trends
        ):
            assert set(item.evidence_refs) <= valid
            assert item.evidence_refs, f"{item.title} has no evidence refs"

    def test_no_fabricated_statistics(self, service):
        solved(service, "a-one", ["Array"], day=0)
        seed_problem(service, "w-one", ["Array"], DifficultyLevel.EASY,
                     [{"status": SubmissionStatus.WRONG_ANSWER, "code": NESTED_CODE}], day=1)
        overview = service.analytics_service.get_overview(account=None)
        profile = _insight(service).profile
        assert profile.total_problems == overview.total_problems
        assert profile.total_solved == overview.accepted_problems
        assert profile.total_submissions == overview.total_submissions
        assert profile.total_attempts == overview.total_attempts

    def test_complexity_claims_declare_their_source(self, service):
        seed_problem(service, "w-one", ["Array"], DifficultyLevel.EASY,
                     [{"status": SubmissionStatus.WRONG_ANSWER, "code": NESTED_CODE}], day=0)
        profile = _insight(service).profile
        for signal in profile.complexity_signals:
            assert signal["source"] in {"code_analysis", "attempt_analysis", "code_estimate"}

    def test_cached_analysis_is_preferred_over_estimate(self, service):
        seed_problem(service, "w-one", ["Array"], DifficultyLevel.EASY,
                     [{"status": SubmissionStatus.WRONG_ANSWER, "code": NESTED_CODE}], day=0)
        problem = service.storage.get_by_slug("w-one")
        service.analyze_submission(problem.attempts[0].submissions[0].id)
        profile = _insight(service).profile
        assert any(s["source"] == "code_analysis" for s in profile.complexity_signals)


class TestDiversity:
    def test_single_topic_does_not_fill_every_strength(self, service):
        solved(service, "h-one", ["Hash Table"], day=0)
        solved(service, "h-two", ["Hash Table"], day=1)
        solved(service, "h-three", ["Hash Table"], day=2)
        insight = _insight(service)
        topic_strengths = [s for s in insight.strengths if "Hash Table" in s.title]
        assert len(topic_strengths) == 1
