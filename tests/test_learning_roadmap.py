"""Regression tests for the hardened learning layer.

Covers the roadmap/recommendation/similarity/optimization requirements:
real candidates only, conceptual (not tag-only) similarity, whole-history
roadmaps, 3-5 problems per phase, global de-duplication, diversity, and honest
handling of missing evidence.
"""

from __future__ import annotations

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from codememory.ai.evidence_models import EvidenceMetrics, InsightEvidence, ProblemSnapshot
from codememory.ai.models import ProblemRecommendation, RoadmapMilestone
from codememory.ai.providers.qwen_provider import Qwen3Provider
from codememory.core.service import CodeMemoryService
from codememory.domain.enums import DifficultyLevel, SubmissionStatus
from codememory.domain.models import Attempt, Problem, Submission
from codememory.learning.candidates import (
    CandidateFilterPolicy,
    filter_candidates,
)
from codememory.learning.models import ProblemCandidate
from codememory.learning.profile import build_learning_profile
from codememory.learning.roadmap import RoadmapOptions, validate_roadmap
from codememory.learning.similarity import SeedContext, score_candidate
from codememory.learning.sources import (
    CompositeProblemSource,
    LeetCodeProblemSource,
    RemoteSourceConfig,
)

BASE_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def service():
    svc = CodeMemoryService(db_path=":memory:")
    yield svc
    svc.close_storage()


def add_problem(
    svc: CodeMemoryService,
    slug: str,
    topics,
    difficulty: DifficultyLevel = DifficultyLevel.EASY,
    statuses=(),
    *,
    code: str = "pass",
    day: int = 0,
    url=None,
):
    problem = Problem(
        id=slug,
        title=slug.replace("-", " ").title(),
        slug=slug,
        difficulty=difficulty,
        platform="LeetCode",
        topics=list(topics),
        url=url,
    )
    for index, status in enumerate(statuses):
        submitted = BASE_TIME + timedelta(days=day, minutes=index)
        problem.attempts.append(
            Attempt(
                problem_id=problem.id,
                attempt_number=index + 1,
                status=status,
                submissions=[
                    Submission(
                        problem_id=problem.id,
                        code=code,
                        language="python",
                        status=status,
                        submitted_at=submitted,
                    )
                ],
            )
        )
    svc.storage.save(problem)
    return problem


_RICH_SOLVED = [
    ("two-sum", ["Array", "Hash Table"], DifficultyLevel.EASY, [SubmissionStatus.ACCEPTED]),
    ("contains-duplicate", ["Array", "Hash Table"], DifficultyLevel.EASY, [SubmissionStatus.ACCEPTED]),
    ("binary-search", ["Binary Search", "Array"], DifficultyLevel.EASY, [SubmissionStatus.ACCEPTED]),
    ("search-insert-position", ["Binary Search", "Array"], DifficultyLevel.EASY, [SubmissionStatus.ACCEPTED]),
    ("valid-parentheses", ["String", "Stack"], DifficultyLevel.EASY, [SubmissionStatus.ACCEPTED]),
    ("merge-two-sorted-lists", ["Linked List", "Recursion"], DifficultyLevel.EASY, [SubmissionStatus.ACCEPTED]),
    (
        "number-of-islands",
        ["Array", "Depth-First Search", "Breadth-First Search", "Union Find", "Matrix"],
        DifficultyLevel.MEDIUM,
        [SubmissionStatus.WRONG_ANSWER, SubmissionStatus.TIME_LIMIT_EXCEEDED, SubmissionStatus.ACCEPTED],
    ),
]

_RICH_CANDIDATES = [
    ("3sum", ["Array", "Two Pointers", "Sorting"], DifficultyLevel.MEDIUM),
    ("container-with-most-water", ["Array", "Two Pointers", "Greedy"], DifficultyLevel.MEDIUM),
    ("longest-substring-without-repeating-characters", ["Hash Table", "String", "Sliding Window"], DifficultyLevel.MEDIUM),
    ("minimum-window-substring", ["Hash Table", "String", "Sliding Window"], DifficultyLevel.HARD),
    ("daily-temperatures", ["Array", "Stack", "Monotonic Stack"], DifficultyLevel.MEDIUM),
    ("invert-binary-tree", ["Tree", "Depth-First Search", "Breadth-First Search", "Binary Tree"], DifficultyLevel.EASY),
    ("binary-tree-level-order-traversal", ["Tree", "Breadth-First Search", "Binary Tree"], DifficultyLevel.MEDIUM),
    ("climbing-stairs", ["Math", "Dynamic Programming", "Memoization"], DifficultyLevel.EASY),
    ("coin-change", ["Array", "Dynamic Programming", "Breadth-First Search"], DifficultyLevel.MEDIUM),
    ("kth-largest-element-in-an-array", ["Array", "Divide and Conquer", "Sorting", "Heap (Priority Queue)"], DifficultyLevel.MEDIUM),
    ("trapping-rain-water", ["Array", "Two Pointers", "Stack", "Monotonic Stack"], DifficultyLevel.HARD),
    ("product-of-array-except-self", ["Array", "Prefix Sum"], DifficultyLevel.MEDIUM),
    ("subarray-sum-equals-k", ["Array", "Hash Table", "Prefix Sum"], DifficultyLevel.MEDIUM),
    ("course-schedule", ["Depth-First Search", "Breadth-First Search", "Graph", "Topological Sort"], DifficultyLevel.MEDIUM),
    ("valid-anagram", ["Hash Table", "String", "Sorting"], DifficultyLevel.EASY),
    ("longest-consecutive-sequence", ["Array", "Hash Table", "Union Find"], DifficultyLevel.MEDIUM),
]


def seed_rich(svc: CodeMemoryService) -> None:
    for index, (slug, topics, difficulty, statuses) in enumerate(_RICH_SOLVED):
        add_problem(svc, slug, topics, difficulty, statuses, day=index)
    for index, (slug, topics, difficulty) in enumerate(_RICH_CANDIDATES):
        add_problem(svc, slug, topics, difficulty, day=index)


def _profile(svc: CodeMemoryService):
    return build_learning_profile(svc.analytics_service, account=None)


def _all_recommendations(roadmap):
    out = []
    for milestone in roadmap.milestones:
        out.extend(milestone.recommended_problems)
    return out


def _rec(slug: str, title: str | None = None) -> ProblemRecommendation:
    return ProblemRecommendation(
        problem_slug=slug,
        title=title or slug,
        difficulty="Medium",
        topics=["Array"],
        selection_rationale="reason",
        target_skill="skill",
        prior_attempt_connection="connection",
        difficulty_rationale="difficulty",
        solving_focus="focus",
        next_step_after="next",
    )


def _milestone(mid: str, order: int, recs) -> RoadmapMilestone:
    return RoadmapMilestone(
        id=mid,
        title=f"Phase {order}",
        order=order,
        learning_objective="objective",
        relevance="rationale",
        recommended_problems=list(recs),
        completion_criteria="done",
        reflection_question="reflect",
    )


# ---------------------------------------------------------------------------
# TEST 1-4: real candidates, exclusions
# ---------------------------------------------------------------------------


class TestCandidateRetrieval:
    def test_recently_solved_produces_related_real_candidates(self, service):
        seed_rich(service)
        catalog = {p.slug for p in service.storage.list_all()}
        recs = service.get_next_problem_recommendations(limit=3)
        assert recs, "Expected at least one recommendation"
        for rec in recs:
            assert rec.problem_slug in catalog
            assert rec.title in {p.title for p in service.storage.list_all()}
            assert rec.similarity_reasons, "Every recommendation must explain itself"

    def test_recently_solved_problem_is_excluded(self, service):
        seed_rich(service)
        profile = _profile(service)
        recs = service.get_next_problem_recommendations(limit=5)
        assert profile.seed_problem_key not in [r.problem_slug for r in recs]

    def test_already_solved_candidate_is_excluded(self, service):
        seeded = add_problem(service, "two-sum", ["Array", "Hash Table"], statuses=[SubmissionStatus.ACCEPTED], day=0)
        add_problem(service, "three-sum", ["Array", "Two Pointers"], day=1)
        catalog = [p for p in service.storage.list_all()]
        profile = _profile(service)
        pool = filter_candidates(
            [ProblemCandidate(problem_id=p.id, slug=p.slug, title=p.title, difficulty="Easy", topics=p.topics) for p in catalog],
            profile=profile,
            policy=CandidateFilterPolicy(exclude_solved=True),
        )
        assert seeded.slug not in [c.slug for c in pool.accepted]

    def test_recently_attempted_excluded_when_policy_requires(self, service):
        problem = add_problem(
            service, "fresh-prob", ["Array"], day=0, statuses=[SubmissionStatus.WRONG_ANSWER]
        )
        # Force the submission to be "now" so it lands in the recent window.
        problem.attempts[0].submissions[0].submitted_at = datetime.now(timezone.utc)
        service.storage.save(problem)
        profile = _profile(service)
        candidate = ProblemCandidate(problem_id=problem.id, slug=problem.slug, title=problem.title, difficulty="Easy", topics=problem.topics)
        lenient = filter_candidates([candidate], profile=profile, policy=CandidateFilterPolicy(exclude_recent=False))
        strict = filter_candidates([candidate], profile=profile, policy=CandidateFilterPolicy(exclude_recent=True))
        assert [c.slug for c in lenient.accepted] == ["fresh-prob"]
        assert strict.accepted == []


# ---------------------------------------------------------------------------
# TEST 5-6: conceptual similarity, not tag-only
# ---------------------------------------------------------------------------


class TestConceptualSimilarity:
    def test_conceptual_similarity_outranks_generic_topic_match(self):
        seed = SeedContext(
            seed_topics=("Array", "Hash Table"),
            seed_patterns=("array_traversal", "hash_lookup", "frequency_counting"),
            difficulty_ceiling="Easy",
        )
        conceptual = ProblemCandidate(
            problem_id="a", slug="valid-anagram", title="Valid Anagram",
            difficulty="Easy", topics=["Hash Table", "String", "Sorting"],
        )
        generic = ProblemCandidate(
            problem_id="b", slug="maximum-subarray", title="Maximum Subarray",
            difficulty="Easy", topics=["Array", "Divide and Conquer", "Dynamic Programming"],
        )
        assert score_candidate(conceptual, seed).total > score_candidate(generic, seed).total

    def test_roadmap_can_select_adjacent_topics(self, service):
        seed_rich(service)
        profile = _profile(service)
        roadmap = service.get_personalized_roadmap()
        seed_topics = set(profile.seed_topics)
        recs = _all_recommendations(roadmap)
        assert any(not (set(r.topics) & seed_topics) for r in recs), (
            "Expected at least one problem in an adjacent (non-seed) topic"
        )


# ---------------------------------------------------------------------------
# TEST 7-13: roadmap quality
# ---------------------------------------------------------------------------


class TestRoadmapQuality:
    def test_roadmap_uses_multiple_historical_solved_problems(self, service):
        seed_rich(service)
        profile = _profile(service)
        assert profile.solved_problems >= 5
        roadmap = service.get_personalized_roadmap()
        target_skills = {s.lower() for m in roadmap.milestones for s in m.concepts_to_study}
        assert len(target_skills) >= 2

    def test_every_phase_has_at_least_three_problems(self, service):
        seed_rich(service)
        roadmap = service.get_personalized_roadmap()
        assert roadmap.milestones
        for milestone in roadmap.milestones:
            assert len(milestone.recommended_problems) >= RoadmapOptions().min_problems_per_phase

    def test_no_problem_appears_in_two_phases(self, service):
        seed_rich(service)
        roadmap = service.get_personalized_roadmap()
        slugs = [r.problem_slug for r in _all_recommendations(roadmap)]
        assert len(slugs) == len(set(slugs))

    def test_no_phase_repeats_a_problem(self, service):
        seed_rich(service)
        roadmap = service.get_personalized_roadmap()
        for milestone in roadmap.milestones:
            slugs = [r.problem_slug for r in milestone.recommended_problems]
            assert len(slugs) == len(set(slugs))

    def test_roadmap_spans_multiple_topics(self, service):
        seed_rich(service)
        roadmap = service.get_personalized_roadmap()
        topics = {t for r in _all_recommendations(roadmap) for t in r.topics}
        assert len(topics) >= 3

    def test_binary_search_history_does_not_fill_every_phase(self, service):
        solved = [
            ("binary-search", ["Binary Search", "Array"]),
            ("search-insert-position", ["Binary Search", "Array"]),
            ("find-first-and-last-position", ["Binary Search", "Array"]),
            ("two-sum", ["Array", "Hash Table"]),
            ("valid-parentheses", ["String", "Stack"]),
        ]
        for index, (slug, topics) in enumerate(solved):
            add_problem(service, slug, topics, DifficultyLevel.EASY, [SubmissionStatus.ACCEPTED], day=index)
        for index, (slug, topics, difficulty) in enumerate(_RICH_CANDIDATES):
            add_problem(service, slug, topics, difficulty, day=index)
        roadmap = service.get_personalized_roadmap()
        assert len(roadmap.milestones) >= 2
        binary_phases = [
            m for m in roadmap.milestones
            if any("binary search" in s.lower() for s in m.concepts_to_study)
        ]
        assert len(binary_phases) < len(roadmap.milestones), (
            "Binary search must not appear in every phase just because it was solved recently"
        )

    def test_difficulty_progression_uses_history(self, service):
        add_problem(service, "easy-one", ["Array", "Hash Table"], DifficultyLevel.EASY, [SubmissionStatus.ACCEPTED], day=0)
        add_problem(service, "easy-two", ["Array", "Two Pointers"], DifficultyLevel.EASY, [SubmissionStatus.ACCEPTED], day=1)
        add_problem(service, "hard-candidate", ["Array", "Hash Table"], DifficultyLevel.HARD, day=2)
        add_problem(service, "medium-candidate-a", ["Array", "Hash Table"], DifficultyLevel.MEDIUM, day=3)
        add_problem(service, "medium-candidate-b", ["Array", "Hash Table"], DifficultyLevel.MEDIUM, day=4)
        add_problem(service, "medium-candidate-c", ["Array", "Hash Table"], DifficultyLevel.MEDIUM, day=5)
        profile = _profile(service)
        assert profile.difficulty_ceiling == "Easy"
        roadmap = service.get_personalized_roadmap()
        difficulties = {r.difficulty for r in _all_recommendations(roadmap)}
        assert "Hard" not in difficulties, "A Hard problem must not be recommended for an Easy-level history"

    def test_unpracticed_topic_is_not_a_weakness(self, service):
        add_problem(service, "array-one", ["Array", "Hash Table"], statuses=[SubmissionStatus.ACCEPTED], day=0)
        profile = _profile(service)
        gap_signals = [s for s in profile.improvement_areas if s.key == "gap.unpracticed_foundations"]
        assert gap_signals, "Unpracticed foundations must be reported as a coverage gap"
        assert gap_signals[0].category == "observed"
        struggle_signals = [s for s in profile.improvement_areas if s.key.startswith("struggle.")]
        unpracticed = set(profile.unpracticed_topics)
        for signal in struggle_signals:
            assert not (set(signal.topics) & unpracticed), (
                "An unpracticed topic must never be labelled a struggle"
            )

    def test_repeated_failures_create_an_improvement_target(self, service):
        add_problem(
            service,
            "slow-prob",
            ["Array", "Two Pointers"],
            DifficultyLevel.MEDIUM,
            [SubmissionStatus.TIME_LIMIT_EXCEEDED, SubmissionStatus.TIME_LIMIT_EXCEEDED, SubmissionStatus.ACCEPTED],
            day=0,
        )
        profile = _profile(service)
        assert any(s.key.startswith("struggle.tle.") for s in profile.improvement_areas)


# ---------------------------------------------------------------------------
# TEST 14-17: optimization explanation
# ---------------------------------------------------------------------------


class TestOptimizationExplanation:
    def test_nested_loop_reports_real_complexity_change(self, service):
        code = (
            "def two_sum(nums, target):\n"
            "    for i in range(len(nums)):\n"
            "        for j in range(i + 1, len(nums)):\n"
            "            if nums[i] + nums[j] == target:\n"
            "                return [i, j]\n"
        )
        add_problem(
            service, "pair-sum", ["Array", "Hash Table"], DifficultyLevel.EASY,
            [SubmissionStatus.ACCEPTED], code=code, day=0,
        )
        result = service.get_optimization_explanation("pair-sum")
        assert "O(n^2)" in result.complexity_comparison.current_time
        assert "O(n)" in result.complexity_comparison.proposed_time
        assert result.transformation_steps, "An optimization must include concrete steps"
        assert result.general_pattern

    def test_missing_source_code_is_reported_honestly(self, service):
        add_problem(
            service, "no-code", ["Tree"], DifficultyLevel.EASY,
            [SubmissionStatus.ACCEPTED], code="", day=0,
        )
        result = service.get_optimization_explanation("no-code")
        assert result.approach_source == "metadata"
        assert "no source code" in result.current_solution_summary.lower()
        assert result.transformation_steps == []

    def test_no_fabricated_urls_or_titles(self, service):
        seed_rich(service)
        catalog = {p.slug: p.title for p in service.storage.list_all()}
        roadmap = service.get_personalized_roadmap()
        for rec in _all_recommendations(roadmap):
            assert rec.title == catalog[rec.problem_slug]
            if rec.url is not None:
                assert rec.url.startswith("https://leetcode.com/problems/")
                assert rec.problem_slug in rec.url


# ---------------------------------------------------------------------------
# TEST 18-19: remote source de-duplication and fallback
# ---------------------------------------------------------------------------


class _StaticSource:
    name = "test"

    def __init__(self, candidates):
        self._candidates = list(candidates)

    def list_candidates(self):
        return list(self._candidates)


class _FailingClient:
    def fetch_problem_list(self, limit=200):
        raise RuntimeError("network unavailable")


class TestProblemSources:
    def test_remote_deduplicated_against_local_catalog(self):
        local = _StaticSource([
            ProblemCandidate(problem_id="1", slug="two-sum", title="Two Sum", difficulty="Easy", topics=["Array"], source="local_catalog"),
        ])
        remote = _StaticSource([
            ProblemCandidate(problem_id="1", slug="two-sum", title="Two Sum", difficulty="Easy", topics=["Array"], source="leetcode"),
            ProblemCandidate(problem_id="2", slug="add-two-numbers", title="Add Two Numbers", difficulty="Medium", topics=["Linked List"], source="leetcode"),
        ])
        merged = CompositeProblemSource([local, remote]).list_candidates()
        assert [c.key for c in merged] == ["two-sum", "add-two-numbers"]
        assert merged[0].source == "local_catalog"

    def test_remote_failure_falls_back_to_local(self):
        # Use a workspace-local temp dir: the sandbox denies pytest's default
        # %TEMP% location on this machine.
        with tempfile.TemporaryDirectory(dir=".") as tmp:
            remote = LeetCodeProblemSource(
                client=_FailingClient(),
                cache_path=Path(tmp) / "cache.json",
                config=RemoteSourceConfig(enabled=True),
            )
            assert remote.list_candidates() == []
            local = _StaticSource([
                ProblemCandidate(problem_id="1", slug="two-sum", title="Two Sum", difficulty="Easy", topics=["Array"], source="local_catalog"),
            ])
            merged = CompositeProblemSource([local, remote]).list_candidates()
            assert [c.slug for c in merged] == ["two-sum"]


# ---------------------------------------------------------------------------
# TEST 20-21: sparse data and Qwen grounding
# ---------------------------------------------------------------------------


class TestSparseAndGrounding:
    def test_sparse_history_produces_cautious_roadmap(self, service):
        add_problem(service, "only-prob", ["Array"], statuses=[SubmissionStatus.ACCEPTED], day=0)
        roadmap = service.get_personalized_roadmap()
        assert roadmap.is_early_stage is True
        assert roadmap.limitations

    def test_qwen_cannot_introduce_unverified_problems(self):
        evidence = InsightEvidence(scope="full_profile")
        evidence.metrics = EvidenceMetrics(
            overview={"total_problems": 6, "total_submissions": 8, "accepted_problems": 6, "unsolved_problems": 0},
        )
        evidence.supporting_problems = [
            ProblemSnapshot(problem_id=s, title=s, slug=s, difficulty="Easy", topics=t, total_attempts=1, status="Solved")
            for s, t in [
                ("two-sum", ["Array", "Hash Table"]),
                ("contains-duplicate", ["Array", "Hash Table"]),
                ("valid-parentheses", ["String", "Stack"]),
                ("merge-two-sorted-lists", ["Linked List", "Recursion"]),
                ("number-of-islands", ["Array", "Depth-First Search", "Breadth-First Search", "Matrix"]),
                ("binary-search", ["Binary Search", "Array"]),
            ]
        ]
        candidates = [
            Problem(
                id=slug, title=slug.replace("-", " ").title(), slug=slug,
                difficulty=difficulty, platform="LeetCode", topics=list(topics),
            )
            for slug, topics, difficulty in _RICH_CANDIDATES
        ]
        allowed = {c.slug for c in candidates}
        provider = Qwen3Provider(custom_client=object())
        roadmap = provider.generate_roadmap(evidence, candidates)
        for rec in _all_recommendations(roadmap):
            assert rec.problem_slug in allowed, (
                "The model must not introduce problems absent from the evidence/candidates"
            )


# ---------------------------------------------------------------------------
# TEST 22-25: validation
# ---------------------------------------------------------------------------


class TestRoadmapValidation:
    def test_validation_rejects_phase_with_fewer_than_three_problems(self):
        milestones = [
            _milestone("p1", 1, [_rec("a"), _rec("b")]),
        ]
        result = validate_roadmap(milestones, {"a", "b"})
        assert result.valid is False
        assert any("minimum" in v for v in result.violations)

    def test_validation_rejects_duplicate_problems_across_phases(self):
        milestones = [
            _milestone("p1", 1, [_rec("a"), _rec("b"), _rec("c")]),
            _milestone("p2", 2, [_rec("a"), _rec("d"), _rec("e")]),
        ]
        result = validate_roadmap(milestones, {"a", "b", "c", "d", "e"})
        assert result.valid is False
        assert any("more than one phase" in v for v in result.violations)

    def test_validation_rejects_unknown_problem(self):
        milestones = [_milestone("p1", 1, [_rec("a"), _rec("b"), _rec("ghost")])]
        result = validate_roadmap(milestones, {"a", "b"})
        assert result.valid is False
        assert any("not in the verified catalog" in v for v in result.violations)

    def test_generated_roadmap_passes_validation(self, service):
        seed_rich(service)
        catalog_keys = {p.slug for p in service.storage.list_all()}
        roadmap = service.get_personalized_roadmap()
        result = validate_roadmap(roadmap.milestones, catalog_keys)
        assert result.valid is True, result.violations
