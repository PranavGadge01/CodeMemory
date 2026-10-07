"""Regression tests for confirmed implementation defects in the five learning features.

Each test class is named after the defect it guards. Tests here use the service
layer directly rather than the HTTP client so they can set up precise conditions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

import pytest

from codememory.core.service import CodeMemoryService
from codememory.domain.models import Attempt, Problem, Submission
from codememory.domain.enums import DifficultyLevel, SubmissionStatus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def bare_service():
    """Real service backed by an in-memory DuckDB — clean slate per test."""
    svc = CodeMemoryService(db_path=":memory:")
    yield svc
    svc.close_storage()


def _problem(slug: str, topics: List[str], *, pid: str | None = None, url: str | None = None) -> Problem:
    return Problem(
        id=pid or slug,
        title=slug.replace("-", " ").title(),
        slug=slug,
        difficulty=DifficultyLevel.EASY,
        platform="LeetCode",
        topics=topics,
        url=url,
    )


def _submission(problem_id: str, *, code: str = "x", status: SubmissionStatus = SubmissionStatus.ACCEPTED) -> Submission:
    return Submission(
        problem_id=problem_id,
        code=code,
        language="python",
        status=status,
        submitted_at=datetime.now(timezone.utc),
    )


def _save(svc: CodeMemoryService, prob: Problem, *submissions: Submission) -> None:
    if submissions:
        attempt = Attempt(
            problem_id=prob.id,
            attempt_number=len(prob.attempts) + 1,
            status=submissions[-1].status,
            submissions=list(submissions),
        )
        prob.attempts.append(attempt)
    svc.storage.save(prob)


# ---------------------------------------------------------------------------
# Defect 1: improvements list fabricates a non-fact for a single failing attempt
# ---------------------------------------------------------------------------

class TestImprovementsFalsePositive:
    """A single wrong-answer attempt must NOT claim an improvement occurred."""

    def test_single_wrong_answer_improvements_is_empty(self, bare_service):
        prob = _problem("coin-change", ["Dynamic Programming"])
        _save(bare_service, prob, _submission(prob.id, status=SubmissionStatus.WRONG_ANSWER))

        result = bare_service.get_attempt_evolution_analysis("coin-change")
        # No genuine improvement took place — the list must not contain fabricated text
        assert result.improvements == [] or all(
            "submitted and recorded" not in imp for imp in result.improvements
        ), (
            "improvements must not fabricate a fact when no improvement occurred; "
            f"got: {result.improvements}"
        )

    def test_single_accepted_improvements_is_empty_or_factual(self, bare_service):
        """Even an accepted first attempt has no prior to compare against."""
        prob = _problem("easy-prob", ["Array"])
        _save(bare_service, prob, _submission(prob.id, status=SubmissionStatus.ACCEPTED))

        result = bare_service.get_attempt_evolution_analysis("easy-prob")
        # Should be empty or contain only factual statements (no "improvement" vs nothing)
        for imp in result.improvements:
            assert "Attempt submitted and recorded" not in imp, (
                f"Fabricated improvement phrase found: {imp!r}"
            )

    def test_genuine_improvement_is_reported(self, bare_service):
        """WA → Accepted across two attempts IS a real improvement."""
        prob = _problem("real-improvement", ["Array"])
        sub1 = _submission(prob.id, status=SubmissionStatus.WRONG_ANSWER)
        sub2 = _submission(prob.id, status=SubmissionStatus.ACCEPTED)
        _save(bare_service, prob, sub1, sub2)

        result = bare_service.get_attempt_evolution_analysis("real-improvement")
        # The heuristic says "resolved previous Wrong Answer verdict" — check for the observable fact
        assert result.improvements, (
            f"Genuine WA→Accepted improvement must appear in improvements list; got empty"
        )
        combined = " ".join(result.improvements)
        assert "resolved" in combined or "resolved" in combined.lower() or "Accepted" in combined or "resolved previous" in combined, (
            f"Improvement text should describe the WA→Accepted resolution; got: {result.improvements}"
        )


# ---------------------------------------------------------------------------
# Defect 2: Fabricated URL in recommendations
# ---------------------------------------------------------------------------

class TestFabricatedUrl:
    """If a problem has no URL in the catalog, the recommendation URL must be None,
    not a fabricated LeetCode URL."""

    def test_missing_catalog_url_is_not_fabricated(self, bare_service):
        # Solved problem (will be excluded)
        solved = _problem("solved-prob", ["Array"], url=None)
        _save(bare_service, solved, _submission(solved.id, status=SubmissionStatus.ACCEPTED))

        # Unsolved candidate with no URL
        candidate = _problem("unknown-platform-prob", ["Graph"], url=None)
        _save(bare_service, candidate)

        recs = bare_service.get_next_problem_recommendations(limit=1)
        assert recs, "Expected at least one recommendation"
        rec = recs[0]
        assert rec.problem_slug == "unknown-platform-prob"
        assert rec.url is None, (
            f"Expected url=None for catalog entry without URL, got: {rec.url!r}"
        )

    def test_real_catalog_url_is_preserved(self, bare_service):
        real_url = "https://leetcode.com/problems/two-sum/"
        solved = _problem("some-solved", ["Array"], url=None)
        _save(bare_service, solved, _submission(solved.id))

        candidate = _problem("two-sum", ["Array", "Hash Table"], url=real_url)
        _save(bare_service, candidate)

        recs = bare_service.get_next_problem_recommendations(limit=1)
        assert recs
        assert recs[0].url == real_url


# ---------------------------------------------------------------------------
# Defect 3: Nested-loop claim for non-brute-force problems
# ---------------------------------------------------------------------------

class TestNestedLoopFalseComplexityClaim:
    """Accepted DP solutions with intentional nested loops must not be labelled
    as 'Brute Force' when the problem is Dynamic Programming."""

    def test_accepted_dp_with_nested_loops_is_not_labelled_brute_force(self, bare_service):
        # Standard Coin Change DP: nested loops are intentional and correct
        dp_code = (
            "dp = [float('inf')] * (amount + 1)\n"
            "dp[0] = 0\n"
            "for coin in coins:\n"
            "    for i in range(coin, amount + 1):\n"
            "        dp[i] = min(dp[i], dp[i - coin] + 1)\n"
            "return dp[amount]\n"
        )
        prob = _problem("coin-change", ["Dynamic Programming"])
        _save(bare_service, prob, _submission(prob.id, code=dp_code, status=SubmissionStatus.ACCEPTED))

        result = bare_service.get_optimization_explanation("coin-change")
        assert result.approach_source == "code_analysis"
        # Must NOT falsely claim brute force for an accepted DP solution
        assert "Brute Force" not in result.current_approach, (
            f"Accepted DP solution incorrectly labelled 'Brute Force': {result.current_approach!r}"
        )

    def test_approach_source_metadata_when_no_code(self, bare_service):
        prob = _problem("no-code-prob", ["Tree"])
        # Submission with empty code
        _save(bare_service, prob, _submission(prob.id, code="", status=SubmissionStatus.ACCEPTED))

        result = bare_service.get_optimization_explanation("no-code-prob")
        assert result.approach_source == "metadata", (
            f"Expected approach_source='metadata' for empty code, got {result.approach_source!r}"
        )

    def test_complexity_strings_are_not_default_placeholder(self, bare_service):
        """When no submission code is available, complexity strings must be marked estimated,
        not left as the Pydantic field default (O(n²))."""
        prob = _problem("metadata-prob", ["String"])
        _save(bare_service, prob, _submission(prob.id, code="", status=SubmissionStatus.ACCEPTED))

        result = bare_service.get_optimization_explanation("metadata-prob")
        cc = result.complexity_comparison
        # When only metadata is available, the strings should be qualified as estimates
        assert "Estimated" in cc.current_time or "estimated" in cc.current_time.lower() or "?" in cc.current_time, (
            f"Complexity should be qualified when code is unavailable; got: {cc.current_time!r}"
        )


# ---------------------------------------------------------------------------
# Defect 4: Slug vs internal storage ID — correct submissions returned
# ---------------------------------------------------------------------------

class TestSlugVsInternalId:
    """The slug-to-ID resolution must return submissions for the correct problem
    even when the problem's internal UUID differs from its public slug."""

    def test_submissions_returned_for_correct_problem_when_slug_differs_from_id(self, bare_service):
        """Problem with internal UUID != slug must return its OWN submissions, not another's."""
        # Problem A: slug 'array-prob', internal ID 'uuid-aaaa'
        prob_a = Problem(
            id="uuid-aaaa",
            title="Array Problem",
            slug="array-prob",
            difficulty=DifficultyLevel.EASY,
            platform="LeetCode",
            topics=["Array"],
        )
        sub_a = Submission(
            problem_id="uuid-aaaa",
            code="solution A",
            language="python",
            status=SubmissionStatus.ACCEPTED,
            submitted_at=datetime.now(timezone.utc),
        )
        _save(bare_service, prob_a, sub_a)

        # Problem B: slug 'tree-prob', internal ID 'uuid-bbbb'
        prob_b = Problem(
            id="uuid-bbbb",
            title="Tree Problem",
            slug="tree-prob",
            difficulty=DifficultyLevel.MEDIUM,
            platform="LeetCode",
            topics=["Tree"],
        )
        sub_b = Submission(
            problem_id="uuid-bbbb",
            code="solution B",
            language="java",
            status=SubmissionStatus.WRONG_ANSWER,
            submitted_at=datetime.now(timezone.utc),
        )
        _save(bare_service, prob_b, sub_b)

        # Fetch analysis for 'array-prob' — must use submissions keyed under uuid-aaaa
        result_a = bare_service.get_attempt_evolution_analysis("array-prob")
        assert result_a.problem_slug == "array-prob"
        assert len(result_a.timeline) == 1
        assert result_a.timeline[0]["submission_id"] == sub_a.id
        assert result_a.timeline[0]["status"] == "Accepted"

        # Fetch analysis for 'tree-prob' — must NOT include sub_a
        result_b = bare_service.get_attempt_evolution_analysis("tree-prob")
        assert result_b.problem_slug == "tree-prob"
        assert len(result_b.timeline) == 1
        assert result_b.timeline[0]["submission_id"] == sub_b.id
        assert result_b.timeline[0]["status"] == "Wrong Answer"

    def test_optimization_uses_most_recent_submission_not_arbitrary_ordering(self, bare_service):
        """The optimization endpoint must use the chronologically latest submission."""
        import time
        prob = Problem(
            id="uuid-zzzz",
            title="Ordered Problem",
            slug="ordered-prob",
            difficulty=DifficultyLevel.MEDIUM,
            platform="LeetCode",
            topics=["Array"],
        )
        sub_old = Submission(
            problem_id="uuid-zzzz",
            code="old code — brute force nested loops",
            language="python",
            status=SubmissionStatus.WRONG_ANSWER,
            submitted_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        time.sleep(0.01)  # ensure ordering
        sub_new = Submission(
            problem_id="uuid-zzzz",
            code="new code — single pass",
            language="python",
            status=SubmissionStatus.ACCEPTED,
            submitted_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
        )
        _save(bare_service, prob, sub_old, sub_new)

        result = bare_service.get_optimization_explanation("ordered-prob")
        # The most recent submission (sub_new) should be used; sub_new has no nested loops
        assert result.submission_id == sub_new.id, (
            f"Expected most-recent submission {sub_new.id!r}, got {result.submission_id!r}"
        )


# ---------------------------------------------------------------------------
# Defect 5: Submission isolation — two problems with overlapping topics
# ---------------------------------------------------------------------------

class TestSubmissionIsolation:
    """Submissions must not be mixed between problems."""

    def test_subs_from_different_problems_are_not_mixed(self, bare_service):
        prob1 = _problem("prob-alpha", ["Array"])
        prob2 = _problem("prob-beta", ["Array"])  # same topic, different problem

        _save(bare_service, prob1, _submission(prob1.id, status=SubmissionStatus.ACCEPTED))
        _save(bare_service, prob2, _submission(prob2.id, status=SubmissionStatus.WRONG_ANSWER))

        result1 = bare_service.get_attempt_evolution_analysis("prob-alpha")
        result2 = bare_service.get_attempt_evolution_analysis("prob-beta")

        assert all(e["status"] == "Accepted" for e in result1.timeline)
        assert all(e["status"] == "Wrong Answer" for e in result2.timeline)
        assert len(result1.timeline) == 1
        assert len(result2.timeline) == 1


# ---------------------------------------------------------------------------
# Defect 6: Recommendation excludes solved problems
# ---------------------------------------------------------------------------

class TestSolvedExclusion:
    """Solved problems must be excluded from next-problem recommendations by default."""

    def test_solved_problem_excluded_from_recommendations(self, bare_service):
        solved = _problem("already-solved", ["Array"])
        _save(bare_service, solved, _submission(solved.id, status=SubmissionStatus.ACCEPTED))

        unsolved = _problem("not-yet-solved", ["Array"])
        _save(bare_service, unsolved)

        recs = bare_service.get_next_problem_recommendations(limit=5)
        slugs = [r.problem_slug for r in recs]
        assert "already-solved" not in slugs, (
            f"Solved problem must not appear in recommendations; got: {slugs}"
        )
        assert "not-yet-solved" in slugs, (
            f"Unsolved problem must appear in recommendations; got: {slugs}"
        )

    def test_partial_solve_wrong_answer_is_not_excluded(self, bare_service):
        """A problem with only a WA submission is NOT solved and should appear."""
        partially_attempted = _problem("partial-prob", ["Graph"])
        _save(bare_service, partially_attempted, _submission(partially_attempted.id, status=SubmissionStatus.WRONG_ANSWER))

        recs = bare_service.get_next_problem_recommendations(limit=5)
        slugs = [r.problem_slug for r in recs]
        assert "partial-prob" in slugs, (
            f"WA-only problem should be recommendable; got: {slugs}"
        )


# ---------------------------------------------------------------------------
# Defect 7: Sample size caveats for tiny histories
# ---------------------------------------------------------------------------

class TestSampleSizeCaveats:
    """Patterns with fewer than 5 problems must include sample-size notes."""

    def test_small_history_includes_sample_size_note(self, bare_service):
        prob = _problem("tiny-catalog", ["Array"])
        _save(bare_service, prob, _submission(prob.id))

        result = bare_service.get_submission_pattern_insights()
        assert result.sample_size_notes, (
            "A history of only 1 problem must produce sample_size_notes"
        )
        combined = " ".join(result.sample_size_notes).lower()
        assert "limited" in combined or "additional" in combined or "small" in combined, (
            f"sample_size_notes must acknowledge limited data: {result.sample_size_notes}"
        )

    def test_zero_history_findings_is_non_empty(self, bare_service):
        """Empty history should still return a valid response (not crash)."""
        result = bare_service.get_submission_pattern_insights()
        assert result.summary is not None
        assert isinstance(result.findings, list)
        # At minimum, the baseline fact finding should always be present
        assert len(result.findings) >= 1


# ---------------------------------------------------------------------------
# Defect 8: Deprecated datetime.utcnow in schema — timezone-awareness check
# ---------------------------------------------------------------------------

class TestSchemaDatetimeAwareness:
    """generated_at in NextProblemsOut and PersonalizedRoadmapOut must be timezone-aware."""

    def test_next_problems_generated_at_is_timezone_aware(self, bare_service):
        # We test the domain model directly since the fix is in the schema
        from codememory.ai.models import PersonalizedRoadmap
        roadmap = PersonalizedRoadmap()
        assert roadmap.generated_at.tzinfo is not None, (
            "PersonalizedRoadmap.generated_at must be timezone-aware"
        )

    def test_schema_generated_at_via_api(self):
        """NextProblemsOut.generated_at must not use deprecated datetime.utcnow()."""
        from api.schemas.learning import NextProblemsOut
        out = NextProblemsOut(recommendations=[])
        assert out.generated_at.tzinfo is not None, (
            "NextProblemsOut.generated_at must be timezone-aware (use datetime.now(timezone.utc))"
        )


# ---------------------------------------------------------------------------
# Defect 9: Deterministic ranking for same input
# ---------------------------------------------------------------------------

class TestDeterministicRanking:
    """Recommendation ranking must be deterministic for identical inputs."""

    def test_same_input_produces_same_order(self, bare_service):
        # Three unsolved problems
        for slug in ["prob-x", "prob-y", "prob-z"]:
            p = _problem(slug, ["Array"])
            _save(bare_service, p)

        recs1 = bare_service.get_next_problem_recommendations(limit=3)
        recs2 = bare_service.get_next_problem_recommendations(limit=3)

        slugs1 = [r.problem_slug for r in recs1]
        slugs2 = [r.problem_slug for r in recs2]
        assert slugs1 == slugs2, (
            f"Ranking must be deterministic: first call {slugs1}, second {slugs2}"
        )


# ---------------------------------------------------------------------------
# Defect 10: Roadmap references only real catalog problems
# ---------------------------------------------------------------------------

class TestRoadmapCatalogGrounding:
    """Roadmap milestones must only reference problems present in the actual catalog."""

    def test_roadmap_recommended_problems_are_in_catalog(self, bare_service):
        # Seed two real problems in the catalog
        prob_a = _problem("real-catalog-a", ["Array", "Hash Table"])
        prob_b = _problem("real-catalog-b", ["Two Pointers"])
        _save(bare_service, prob_a)
        _save(bare_service, prob_b)

        roadmap = bare_service.get_personalized_roadmap()
        catalog_slugs = {"real-catalog-a", "real-catalog-b"}

        for milestone in roadmap.milestones:
            for rec in milestone.recommended_problems:
                assert rec.problem_slug in catalog_slugs, (
                    f"Roadmap references problem '{rec.problem_slug}' not in catalog: {catalog_slugs}"
                )

    def test_empty_catalog_roadmap_has_no_recommended_problems(self, bare_service):
        """Empty catalog: milestones are generated but no problem recommendations are fabricated."""
        roadmap = bare_service.get_personalized_roadmap()
        for milestone in roadmap.milestones:
            assert milestone.recommended_problems == [], (
                f"Milestone '{milestone.title}' fabricated problem recommendations with empty catalog"
            )
