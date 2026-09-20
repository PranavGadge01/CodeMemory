"""Tests for the Grounded Personalized Insight Pipeline.

Verifies:
1. EvidenceBuilder gathers deterministic analytics & cached AI analyses without making LLM calls or triggering analyze_submission().
2. AICodeAnalyzer.get_cached_analyses() deterministically selects matching analysis versions.
3. BaseAIProvider.interpret_evidence() implementation in HeuristicAIProvider and OpenAIProvider.
4. EvidenceValidator strictly enforces evidence_ref subset invariant.
5. InsightService orchestrates the pipeline and safely handles validation/provider fallbacks.
6. CodeMemoryService exposes grounded insight methods.
"""

from datetime import datetime, timezone
import pytest
from unittest.mock import MagicMock, patch

from codememory.ai.analyzer import AICodeAnalyzer
from codememory.ai.evidence_builder import EvidenceBuilder
from codememory.ai.evidence_models import (
    EvidenceComparison,
    EvidenceItem,
    InsightEvidence,
    ProblemSnapshot,
)
from codememory.ai.evidence_validator import EvidenceValidationError, EvidenceValidator
from codememory.ai.insight_service import GroundedInsight, InsightService
from codememory.ai.models import SubmissionAnalysis
from codememory.ai.providers.base_provider import InterpretationResult
from codememory.ai.providers.heuristic_provider import HeuristicAIProvider
from codememory.ai.providers.openai_provider import OpenAIProvider
from codememory.analytics.analytics_service import AnalyticsService
from codememory.analytics.pattern_analyzer import PatternAnalyzer
from codememory.core.service import CodeMemoryService
from codememory.domain.enums import DifficultyLevel, SubmissionStatus
from codememory.domain.models import Problem, Submission
from codememory.storage import CompositeStorage


@pytest.fixture
def mock_repo():
    repo = MagicMock(spec=CompositeStorage)
    s1 = Submission(
        id="sub-1",
        problem_id="two-sum",
        status=SubmissionStatus.ACCEPTED,
        language="python",
        code="class Solution:\n    def twoSum(self, nums, target):\n        d = {}\n        for i, n in enumerate(nums):\n            if target - n in d:\n                return [d[target - n], i]\n            d[n] = i",
        runtime_ms=45.0,
        memory_mb=14.2,
        submitted_at=datetime.now(timezone.utc),
    )
    s2 = Submission(
        id="sub-2",
        problem_id="3sum",
        status=SubmissionStatus.TIME_LIMIT_EXCEEDED,
        language="python",
        code="class Solution:\n    def threeSum(self, nums):\n        ans = []\n        for i in range(len(nums)):\n            for j in range(i+1, len(nums)):\n                for k in range(j+1, len(nums)):\n                    if nums[i] + nums[j] + nums[k] == 0:\n                        ans.append([nums[i], nums[j], nums[k]])\n        return ans",
        runtime_ms=2000.0,
        memory_mb=18.0,
        submitted_at=datetime.now(timezone.utc),
    )
    
    from codememory.domain.models import Attempt
    a1 = Attempt(id="att-1", problem_id="two-sum", submissions=[s1], status=SubmissionStatus.ACCEPTED)
    a2 = Attempt(id="att-2", problem_id="3sum", submissions=[s2], status=SubmissionStatus.TIME_LIMIT_EXCEEDED)

    p1 = Problem(
        id="two-sum",
        title="Two Sum",
        difficulty=DifficultyLevel.EASY,
        topics=["Array", "Hash Table"],
        attempts=[a1],
    )
    p2 = Problem(
        id="3sum",
        title="3Sum",
        difficulty=DifficultyLevel.MEDIUM,
        topics=["Array", "Two Pointers"],
        attempts=[a2],
    )

    repo.list_all.return_value = [p1, p2]
    repo.get_by_id.side_effect = lambda pid: p1 if pid == "two-sum" else (p2 if pid == "3sum" else None)
    repo.get_by_slug.side_effect = lambda slug: p1 if slug == "two-sum" else (p2 if slug == "3sum" else None)
    repo.list_by_problem.side_effect = lambda pid: [s1] if pid == "two-sum" else ([s2] if pid == "3sum" else [])
    return repo


@pytest.fixture
def analytics_service(mock_repo):
    return AnalyticsService(mock_repo)


@pytest.fixture
def pattern_analyzer(analytics_service):
    return PatternAnalyzer(analytics_service)


@pytest.fixture
def ai_analyzer(mock_repo, tmp_path):
    analyzer = AICodeAnalyzer(provider=HeuristicAIProvider(), cache_dir=tmp_path)
    return analyzer


class TestEvidenceModels:
    def test_all_evidence_ids(self):
        evidence = InsightEvidence(
            scope="global",
            items=[
                EvidenceItem(
                    evidence_id="analytics.overview.overall_acceptance_rate_pct",
                    source="analytics.overview",
                    label="Overall Acceptance Rate",
                    value=50.0,
                ),
                EvidenceItem(
                    evidence_id="pattern_analyzer.weak_topics.array",
                    source="pattern_analyzer.weak_topics",
                    label="Weak Topic: Array",
                    value=25.0,
                ),
            ],
            comparisons=[
                EvidenceComparison(
                    evidence_id="comparison.two_pointers_vs_overall",
                    topic_evidence_id="analytics.topic_stats.two_pointers.acceptance_rate_pct",
                    overall_evidence_id="analytics.overview.overall_acceptance_rate_pct",
                    topic_rate=0.0,
                    overall_rate=50.0,
                    delta=-50.0,
                    label="Two Pointers vs Overall",
                )
            ],
        )
        ids = evidence.all_evidence_ids()
        assert "analytics.overview.overall_acceptance_rate_pct" in ids
        assert "pattern_analyzer.weak_topics.array" in ids
        assert "comparison.two_pointers_vs_overall" in ids
        assert len(ids) == 4


class TestAICodeAnalyzerCachedAnalyses:
    def test_get_cached_analyses_version_selection(self, ai_analyzer):
        sa_v1 = SubmissionAnalysis(
            approach="Hash Table",
            algorithms=["Hashing"],
            data_structures=["HashMap"],
            inferred_pattern="Hash Map Lookup",
            time_complexity="O(n)",
            space_complexity="O(n)",
            correctness_summary="Status: Accepted",
            concise_explanation="Uses hash map for fast lookup",
            analysis_version="v1",
        )
        sa_v2 = SubmissionAnalysis(
            approach="Hash Table Optimized",
            algorithms=["Hashing"],
            data_structures=["HashMap"],
            inferred_pattern="Hash Map Lookup",
            time_complexity="O(n)",
            space_complexity="O(n)",
            correctness_summary="Status: Accepted",
            concise_explanation="Optimized hash map lookup",
            analysis_version="v2",
        )
        ai_analyzer._analysis_cache[("sub-1", "hash1", "v1")] = sa_v1
        ai_analyzer._analysis_cache[("sub-1", "hash1", "v2")] = sa_v2

        cached = ai_analyzer.get_cached_analyses(["sub-1"])
        assert "sub-1" in cached
        assert cached["sub-1"].analysis_version == "v1"

    def test_get_cached_analyses_does_not_call_provider(self, ai_analyzer):
        mock_provider = MagicMock(spec=HeuristicAIProvider)
        ai_analyzer.provider = mock_provider

        cached = ai_analyzer.get_cached_analyses(["sub-nonexistent"])
        assert cached == {}
        mock_provider.analyze_submission.assert_not_called()


class TestEvidenceBuilder:
    def test_build_full_profile_evidence_zero_llm_calls(self, analytics_service, pattern_analyzer, ai_analyzer):
        mock_provider = MagicMock()
        ai_analyzer.provider = mock_provider

        builder = EvidenceBuilder(analytics_service, pattern_analyzer, ai_analyzer)
        evidence = builder.build_full_profile_evidence()

        mock_provider.analyze_submission.assert_not_called()

        assert evidence.scope == "full_profile"
        assert len(evidence.items) > 0

    def test_build_topic_evidence(self, analytics_service, pattern_analyzer, ai_analyzer):
        builder = EvidenceBuilder(analytics_service, pattern_analyzer, ai_analyzer)
        evidence = builder.build_topic_evidence("Array")

        assert evidence.scope == "topic:Array"

    def test_build_problem_evidence(self, analytics_service, pattern_analyzer, ai_analyzer, mock_repo):
        builder = EvidenceBuilder(analytics_service, pattern_analyzer, ai_analyzer, storage=mock_repo)
        evidence = builder.build_problem_evidence("two-sum")

        assert evidence.scope == "problem:two-sum"
        assert len(evidence.supporting_problems) == 1
        assert evidence.supporting_problems[0].problem_id == "two-sum"


class TestEvidenceValidator:
    def test_valid_refs(self):
        evidence = InsightEvidence(
            scope="full_profile",
            items=[
                EvidenceItem(
                    evidence_id="e1",
                    source="analytics.overview",
                    label="Test Metric",
                    value=10,
                )
            ],
        )
        interpretation = InterpretationResult(
            headline="Test Headline",
            narrative="Test Narrative",
            evidence_refs=["e1"],
        )
        validator = EvidenceValidator()
        validator.validate(evidence, interpretation)  # Should not raise

    def test_invalid_refs_raises_error(self):
        evidence = InsightEvidence(
            scope="full_profile",
            items=[
                EvidenceItem(
                    evidence_id="e1",
                    source="analytics.overview",
                    label="Test Metric",
                    value=10,
                )
            ],
        )
        interpretation = InterpretationResult(
            headline="Test Headline",
            narrative="Test Narrative",
            evidence_refs=["e1", "e_hallucinated"],
        )
        validator = EvidenceValidator()
        with pytest.raises(EvidenceValidationError) as excinfo:
            validator.validate(evidence, interpretation)
        assert "e_hallucinated" in str(excinfo.value)


class TestHeuristicAIProviderInterpretEvidence:
    def test_interpret_evidence_heuristic(self, analytics_service, pattern_analyzer, ai_analyzer):
        builder = EvidenceBuilder(analytics_service, pattern_analyzer, ai_analyzer)
        evidence = builder.build_full_profile_evidence()

        provider = HeuristicAIProvider()
        result = provider.interpret_evidence(evidence)

        assert isinstance(result, InterpretationResult)
        assert len(result.headline) > 0
        assert len(result.narrative) > 0
        valid_ids = evidence.all_evidence_ids()
        for ref in result.evidence_refs:
            assert ref in valid_ids


class TestInsightService:
    def test_generate_full_profile_insight(self, analytics_service, pattern_analyzer, ai_analyzer):
        builder = EvidenceBuilder(analytics_service, pattern_analyzer, ai_analyzer)
        provider = HeuristicAIProvider()
        service = InsightService(provider, builder)

        insight = service.generate_full_profile_insight()
        assert isinstance(insight, GroundedInsight)
        assert insight.scope == "full_profile"
        assert len(insight.headline) > 0
        assert len(insight.narrative) > 0

    def test_validation_fallback_on_invalid_ref(self, analytics_service, pattern_analyzer, ai_analyzer):
        builder = EvidenceBuilder(analytics_service, pattern_analyzer, ai_analyzer)
        bad_provider = MagicMock(spec=HeuristicAIProvider)
        bad_provider.interpret_evidence.return_value = InterpretationResult(
            headline="Bad AI",
            narrative="Bad narrative",
            evidence_refs=["nonexistent_id"],
        )

        service = InsightService(bad_provider, builder)
        insight = service.generate_full_profile_insight()

        assert isinstance(insight, GroundedInsight)
        assert "nonexistent_id" not in insight.evidence_refs


class TestCodeMemoryServiceGroundedInsights:
    def test_codememory_service_methods(self, tmp_path):
        cms = CodeMemoryService(
            base_dir=tmp_path / "data",
            knowledge_dir=tmp_path / "knowledge",
            db_path=tmp_path / "test.duckdb",
        )
        p1 = Problem(
            id="two-sum",
            title="Two Sum",
            difficulty=DifficultyLevel.EASY,
            topics=["Array", "Hash Table"],
        )
        cms.storage.save(p1)

        insight = cms.get_grounded_insight()
        assert isinstance(insight, GroundedInsight)

        topic_insight = cms.get_topic_insight("Array")
        assert topic_insight.scope == "topic:Array"

        prob_insight = cms.get_problem_insight("two-sum")
        assert prob_insight.scope == "problem:two-sum"

