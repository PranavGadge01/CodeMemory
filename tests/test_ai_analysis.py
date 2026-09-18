"""Tests for AI solution analysis provider."""

from codememory.ai.fallback_provider import HeuristicAIProvider
from codememory.domain.enums import DifficultyLevel, SubmissionStatus
from codememory.domain.models import Problem, Submission


def test_heuristic_ai_provider_analysis():
    provider = HeuristicAIProvider()
    problem = Problem(title="Two Sum", slug="two-sum", difficulty=DifficultyLevel.EASY, topics=["Array", "Hash Table"])

    sub_tle = Submission(
        problem_id=problem.id,
        code="def twoSum(nums, target):\n for i in range(len(nums)):\n  for j in range(i+1, len(nums)):\n   if nums[i] + nums[j] == target: return [i,j]",
        language="python",
        status=SubmissionStatus.TIME_LIMIT_EXCEEDED,
    )

    res_tle = provider.analyze_submission(sub_tle, problem)
    assert res_tle.time_complexity == "O(n²)"
    assert res_tle.possible_mistake is not None
    assert "Time Limit Exceeded" in res_tle.possible_mistake

    sub_acc = Submission(
        problem_id=problem.id,
        code="def twoSum(nums, target):\n hashmap = {}\n for i, n in enumerate(nums):\n  if target - n in hashmap: return [hashmap[target - n], i]\n  hashmap[n] = i",
        language="python",
        status=SubmissionStatus.ACCEPTED,
        runtime_ms=45.0,
    )

    res_acc = provider.analyze_submission(sub_acc, problem, previous_submission=sub_tle)
    assert res_acc.time_complexity == "O(n)"
    assert "Hash Table" in res_acc.inferred_approach or "HashMap" in res_acc.algorithm_ds
    assert res_acc.improvement_over_previous is not None
