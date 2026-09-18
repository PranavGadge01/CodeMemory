"""Tests for lightweight DSA Knowledge Graph builder."""

from codememory.domain.enums import DifficultyLevel, SubmissionStatus
from codememory.domain.models import Problem, Submission
from codememory.graph.knowledge_graph import KnowledgeGraphBuilder


def test_knowledge_graph_construction():
    builder = KnowledgeGraphBuilder()
    p1 = Problem(title="Two Sum", slug="two-sum", difficulty=DifficultyLevel.EASY, topics=["Array", "Hash Table"])
    p2 = Problem(title="3Sum", slug="3sum", difficulty=DifficultyLevel.MEDIUM, topics=["Array", "Hash Table", "Two Pointers"])
    s1 = Submission(problem_id=p1.id, code="def twoSum(): pass", language="python", status=SubmissionStatus.ACCEPTED)
    s2 = Submission(problem_id=p2.id, code="def threeSum(): pass", language="python", status=SubmissionStatus.ACCEPTED)

    graph = builder.build_graph([p1, p2], [s1, s2])
    assert len(graph.nodes) > 0
    assert len(graph.edges) > 0

    # Verify RELATED_TO edge between p1 and p2 due to shared topics Array and Hash Table
    related_edges = [e for e in graph.edges if e.relationship == "RELATED_TO"]
    assert len(related_edges) >= 1
