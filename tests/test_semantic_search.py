"""Tests for local TF-IDF semantic search engine."""

from codememory.domain.enums import DifficultyLevel, SubmissionStatus
from codememory.domain.models import Problem, Submission
from codememory.search.semantic_search import LocalSemanticSearchEngine


def test_local_semantic_search():
    engine = LocalSemanticSearchEngine()
    p1 = Problem(title="Longest Substring Without Repeating Characters", slug="longest-substring", difficulty=DifficultyLevel.MEDIUM, topics=["Sliding Window", "Hash Table"], statement="Find longest substring without repeating characters.")
    s1 = Submission(problem_id=p1.id, code="left = 0; seen = {}", status=SubmissionStatus.ACCEPTED)

    p2 = Problem(title="Two Sum", slug="two-sum", difficulty=DifficultyLevel.EASY, topics=["Array", "Hash Table"], statement="Find two numbers summing to target.")
    s2 = Submission(problem_id=p2.id, code="seen = {}", status=SubmissionStatus.ACCEPTED)

    engine.index_dataset([p1, p2], [s1, s2])

    results = engine.search("problems where I used sliding window")
    assert len(results) >= 1
    assert results[0].problem.title == "Longest Substring Without Repeating Characters"
    assert results[0].relevance_score > 0
