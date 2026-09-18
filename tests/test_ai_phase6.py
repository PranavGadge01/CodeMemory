"""End-to-End & Unit Tests for Phase 6 AI Code Analysis, Solution Evolution, Caching, and Ask CodeMemory."""

from pathlib import Path
import pytest

from codememory.ai.analyzer import AICodeAnalyzer, compute_code_hash
from codememory.ai.context_builder import ContextBuilder
from codememory.ai.memory_service import MemoryService
from codememory.ai.models import SubmissionAnalysis, SolutionEvolution
from codememory.ai.providers.heuristic_provider import HeuristicAIProvider
from codememory.ai.providers.openai_provider import OpenAIProvider
from codememory.core.service import CodeMemoryService
from codememory.domain.enums import DifficultyLevel, SubmissionStatus
from codememory.domain.models import Problem, Submission


class MockAIProvider(HeuristicAIProvider):
    """Mock AI Provider tracking API invocation counts for cache testing."""

    def __init__(self):
        super().__init__()
        self.analyze_call_count = 0
        self.evolution_call_count = 0

    def analyze_submission(self, submission, problem, previous_submission=None):
        self.analyze_call_count += 1
        return super().analyze_submission(submission, problem, previous_submission)

    def analyze_evolution(self, problem, submissions):
        self.evolution_call_count += 1
        return super().analyze_evolution(problem, submissions)


def test_heuristic_provider_single_submission_analysis():
    provider = HeuristicAIProvider()
    problem = Problem(title="Two Sum", slug="two-sum", difficulty=DifficultyLevel.EASY, topics=["Array", "Hash Table"])

    # Failed TLE submission
    sub_tle = Submission(
        problem_id=problem.id,
        code="def twoSum(nums, target):\n for i in range(len(nums)):\n  for j in range(i+1, len(nums)):\n   if nums[i]+nums[j]==target: return [i,j]",
        language="python",
        status=SubmissionStatus.TIME_LIMIT_EXCEEDED,
    )
    res_tle = provider.analyze_submission(sub_tle, problem)
    assert res_tle.time_complexity == "O(n²)"
    assert len(res_tle.certain_facts) >= 2
    assert any("Time Limit Exceeded" in s for s in res_tle.likely_explanations)

    # Accepted HashMap submission
    sub_acc = Submission(
        problem_id=problem.id,
        code="def twoSum(nums, target):\n seen = {}\n for i, n in enumerate(nums):\n  if target - n in seen: return [seen[target - n], i]\n  seen[n] = i",
        language="python",
        status=SubmissionStatus.ACCEPTED,
        runtime_ms=42.0,
    )
    res_acc = provider.analyze_submission(sub_acc, problem, previous_submission=sub_tle)
    assert res_acc.time_complexity == "O(n)"
    assert "Hash Table Lookup" in res_acc.approach or "HashMap" in res_acc.data_structures


def test_failed_attempt_analysis_distinguishes_facts_and_hypotheses():
    provider = HeuristicAIProvider()
    problem = Problem(title="Binary Search", slug="binary-search", difficulty=DifficultyLevel.EASY, topics=["Binary Search"])

    sub_wa = Submission(
        problem_id=problem.id,
        code="def search(nums, target):\n l, r = 0, len(nums)\n while l < r:\n  m = (l+r)//2\n  if nums[m] == target: return m\n  elif nums[m] < target: l = m\n  else: r = m\n return -1",
        language="python",
        status=SubmissionStatus.WRONG_ANSWER,
    )
    analysis = provider.analyze_submission(sub_wa, problem)
    assert analysis.certain_facts is not None
    assert any("Wrong Answer" in f or "WRONG_ANSWER" in f for f in analysis.certain_facts)
    assert any("edge" in exp.lower() or "boundary" in exp.lower() or "wrong answer" in exp.lower() for exp in analysis.likely_explanations)


def test_ai_analyzer_caching_behavior(tmp_path: Path):
    mock_provider = MockAIProvider()
    analyzer = AICodeAnalyzer(provider=mock_provider, cache_dir=tmp_path, analysis_version="v1")

    problem = Problem(title="Two Sum", slug="two-sum")
    sub = Submission(
        problem_id=problem.id,
        code="def twoSum(nums, target): pass",
        language="python",
        status=SubmissionStatus.ACCEPTED,
    )

    # First call -> triggers provider
    res1 = analyzer.analyze_submission(sub, problem)
    assert mock_provider.analyze_call_count == 1

    # Second call with same submission & code -> returns cached, NO new provider call
    res2 = analyzer.analyze_submission(sub, problem)
    assert mock_provider.analyze_call_count == 1
    assert res1.approach == res2.approach

    # Modify code -> triggers new analysis
    sub_modified = Submission(
        id=sub.id,
        problem_id=problem.id,
        code="def twoSum(nums, target):\n hashmap = {}\n for i, n in enumerate(nums):\n  if target - n in hashmap: return [hashmap[target - n], i]\n  hashmap[n] = i",
        language="python",
        status=SubmissionStatus.ACCEPTED,
    )
    res3 = analyzer.analyze_submission(sub_modified, problem)
    assert mock_provider.analyze_call_count == 2
    assert res3.time_complexity == "O(n)"

    # Change prompt analysis version -> triggers new analysis
    analyzer_v2 = AICodeAnalyzer(provider=mock_provider, cache_dir=tmp_path, analysis_version="v2")
    analyzer_v2.analyze_submission(sub_modified, problem)
    assert mock_provider.analyze_call_count == 3


def test_openai_provider_fallback_when_disabled_or_no_key():
    provider = OpenAIProvider(api_key=None)
    assert not provider.is_available()

    problem = Problem(title="Test Prob", slug="test-prob")
    sub = Submission(problem_id=problem.id, code="print('hello')", status=SubmissionStatus.ACCEPTED)

    # Should fall back cleanly to HeuristicAIProvider without crashing
    res = provider.analyze_submission(sub, problem)
    assert isinstance(res, SubmissionAnalysis)
    assert res.approach is not None


def test_solution_evolution_analysis():
    provider = HeuristicAIProvider()
    problem = Problem(title="Two Sum", slug="two-sum", difficulty=DifficultyLevel.EASY)

    sub1 = Submission(
        problem_id=problem.id,
        code="def twoSum(nums, target):\n for i in range(len(nums)):\n  for j in range(i+1, len(nums)):\n   if nums[i]+nums[j]==target: return [i,j]",
        status=SubmissionStatus.TIME_LIMIT_EXCEEDED,
    )
    sub2 = Submission(
        problem_id=problem.id,
        code="def twoSum(nums, target):\n hashmap = {}\n for i, n in enumerate(nums):\n  if target - n in hashmap: return [hashmap[target], i]\n  hashmap[n] = i",
        status=SubmissionStatus.WRONG_ANSWER,
    )
    sub3 = Submission(
        problem_id=problem.id,
        code="def twoSum(nums, target):\n hashmap = {}\n for i, n in enumerate(nums):\n  if target - n in hashmap: return [hashmap[target - n], i]\n  hashmap[n] = i",
        status=SubmissionStatus.ACCEPTED,
        runtime_ms=45.0,
    )

    evolution = provider.analyze_evolution(problem, [sub1, sub2, sub3])
    assert isinstance(evolution, SolutionEvolution)
    assert evolution.total_attempts == 3
    assert len(evolution.steps) == 3
    assert evolution.steps[0].status == "Time Limit Exceeded"
    assert evolution.steps[2].status == "Accepted"
    assert evolution.overall_summary is not None


def test_context_builder_and_ask_codememory_grounded_qa(tmp_path: Path):
    db_path = tmp_path / "test_ai.duckdb"
    service = CodeMemoryService(base_dir=tmp_path, knowledge_dir=tmp_path / "knowledge", db_path=db_path)

    # First add problem to service
    service.add_problem(title="Two Sum", slug="two-sum", difficulty=DifficultyLevel.EASY, topics=["Array", "Hash Table"])

    # Add submissions
    prob, sub1 = service.add_submission(
        problem_identifier="two-sum",
        code="def twoSum(nums, target):\n for i in range(len(nums)):\n  for j in range(i+1, len(nums)):\n   if nums[i]+nums[j]==target: return [i,j]",
        language="python",
        status=SubmissionStatus.TIME_LIMIT_EXCEEDED,
    )
    _, sub2 = service.add_submission(
        problem_identifier="two-sum",
        code="def twoSum(nums, target):\n seen = {}\n for i, n in enumerate(nums):\n  if target - n in seen: return [seen[target - n], i]\n  seen[n] = i",
        language="python",
        status=SubmissionStatus.ACCEPTED,
        runtime_ms=40.0,
    )

    # Test Ask CodeMemory
    res = service.ask_codememory("How did my solution evolve for Two Sum?")
    assert "Two Sum" in res["answer"] or len(res["sources"]) > 0
    assert any(s["title"] == "Two Sum" for s in res["sources"])

    # Test Single Submission Analysis via Service
    sa = service.analyze_submission(sub2.id)
    assert isinstance(sa, SubmissionAnalysis)
    assert sa.time_complexity == "O(n)"

    # Verify original submission records remain 100% UNCHANGED
    prob_reloaded = service.get_problem("two-sum")
    reloaded_subs = [s for a in prob_reloaded.attempts for s in a.submissions]
    assert len(reloaded_subs) == 2
    assert reloaded_subs[0].status == SubmissionStatus.TIME_LIMIT_EXCEEDED
    assert reloaded_subs[1].status == SubmissionStatus.ACCEPTED
    assert reloaded_subs[1].runtime_ms == 40.0
