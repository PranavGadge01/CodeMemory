import pytest
from datetime import datetime, timezone, timedelta

from fastapi.testclient import TestClient
from codememory.core.service import CodeMemoryService
from codememory.domain.models import Problem, Submission, Attempt
from codememory.domain.enums import DifficultyLevel, SubmissionStatus
from api.app import create_app
from api.dependencies import get_service


@pytest.fixture
def cluster_service():
    """Service with multiple problems sharing topics for cluster testing."""
    service = CodeMemoryService(db_path=":memory:")

    # Two problems sharing "Array" topic
    p1 = Problem(title="Two Sum", slug="two-sum", difficulty=DifficultyLevel.EASY, topics=["Array", "Hash Table"])
    p2 = Problem(title="3Sum", slug="3sum", difficulty=DifficultyLevel.MEDIUM, topics=["Array", "Two Pointers"])
    # One problem with only a unique topic
    p3 = Problem(title="LRU Cache", slug="lru-cache", difficulty=DifficultyLevel.HARD, topics=["Design"])

    service.storage.save(p1)
    service.storage.save(p2)
    service.storage.save(p3)

    yield service
    service.close_storage()


@pytest.fixture
def cluster_client(cluster_service):
    app = create_app(service=cluster_service)
    app.dependency_overrides[get_service] = lambda: cluster_service
    with TestClient(app) as client:
        yield client


def test_knowledge_empty_database(empty_client):
    """Empty database should return empty graph and entity counts."""
    response = empty_client.get("/api/v1/knowledge")
    assert response.status_code == 200
    data = response.json()
    assert "graph" in data
    assert "clusters" in data
    assert "entityCounts" in data
    assert data["graph"]["nodes"] == []
    assert data["graph"]["edges"] == []
    assert data["clusters"] == []


def test_knowledge_entity_counts(cluster_client):
    """Knowledge endpoint should return entity counts for the snapshot header."""
    response = cluster_client.get("/api/v1/knowledge")
    assert response.status_code == 200
    data = response.json()

    # Should have entity counts for each node type
    entity_counts = data["entityCounts"]
    assert "Problem" in entity_counts
    assert "Topic" in entity_counts
    # Since clusters are deprecated, they should be empty
    assert data["clusters"] == []


def test_knowledge_graph_has_nodes_and_edges(cluster_client):
    """The knowledge graph should have nodes and edges."""
    response = cluster_client.get("/api/v1/knowledge")
    assert response.status_code == 200
    data = response.json()

    graph = data["graph"]
    assert "nodes" in graph
    assert "edges" in graph
    assert len(graph["nodes"]) > 0
    assert len(graph["edges"]) > 0


def test_knowledge_nodes_have_required_fields(cluster_client):
    """Each node should have id, label, and type."""
    response = cluster_client.get("/api/v1/knowledge")
    assert response.status_code == 200
    data = response.json()

    for node in data["graph"]["nodes"]:
        assert "id" in node
        assert "label" in node
        assert "type" in node


def test_knowledge_problem_nodes_have_extended_fields(cluster_client):
    """Problem nodes should have difficulty, topics, and connectionCount."""
    response = cluster_client.get("/api/v1/knowledge")
    assert response.status_code == 200
    data = response.json()

    problem_nodes = [n for n in data["graph"]["nodes"] if n["type"] == "Problem"]
    for node in problem_nodes:
        # These fields should exist on Problem nodes
        assert "difficulty" in node
        assert "topics" in node


def test_knowledge_clusters_deprecated(cluster_client):
    """Clusters are deprecated and should be empty in Knowledge endpoint."""
    response = cluster_client.get("/api/v1/knowledge")
    assert response.status_code == 200
    data = response.json()

    # Clusters should be empty - this is now Analytics' responsibility
    assert data["clusters"] == []


def test_knowledge_graph_still_present(cluster_client):
    """The knowledge graph should still be returned."""
    response = cluster_client.get("/api/v1/knowledge")
    assert response.status_code == 200
    data = response.json()

    graph = data["graph"]
    assert "nodes" in graph
    assert "edges" in graph
    assert len(graph["nodes"]) > 0
    assert len(graph["edges"]) > 0


def test_knowledge_problem_has_extended_data_with_submissions():
    """Problems with submissions should have language and approach info."""
    service = CodeMemoryService(db_path=":memory:")

    # Create problem with attempts and submissions
    p1 = Problem(
        title="Two Sum",
        slug="two-sum-test",
        difficulty=DifficultyLevel.EASY,
        topics=["Array", "Hash Table"]
    )
    attempt = Attempt(
        problem_id=p1.id,
        attempt_number=1,
        approach_summary="Hash Map Solution",
        reasoning="Use a hash map for O(n) lookup",
        mistakes=["Forgot to check for empty input"]
    )
    sub = Submission(
        problem_id=p1.id,
        code="def twoSum(nums, target): pass",
        language="python",
        status=SubmissionStatus.ACCEPTED,
        attempt_id=attempt.id
    )
    attempt.submissions.append(sub)
    attempt.problem_id = p1.id
    p1.attempts.append(attempt)

    service.storage.save(p1)

    app = create_app(service=service)
    app.dependency_overrides[get_service] = lambda: service
    with TestClient(app) as client:
        response = client.get("/api/v1/knowledge")
        assert response.status_code == 200
        data = response.json()

        problem_nodes = [n for n in data["graph"]["nodes"] if n["type"] == "Problem"]
        assert len(problem_nodes) >= 1, f"Expected at least 1 problem node, got {len(problem_nodes)}, nodes: {[n['id'] for n in problem_nodes]}"

        # Find our problem by checking topics or title
        our_problem = None
        for node in problem_nodes:
            if "Array" in (node.get("topics") or []):
                our_problem = node
                break
            if node.get("label") == "Two Sum":
                our_problem = node

        assert our_problem is not None, f"Could not find Two Sum problem node. Available: {problem_nodes}"

        assert our_problem["difficulty"] == "Easy"
        assert "Array" in our_problem["topics"]
        assert "Hash Table" in our_problem["topics"]
        assert "Python" in our_problem["languages"]
        assert "Hash Map Solution" in our_problem["approaches"]
        assert "Forgot to check for empty input" in our_problem["mistakes"]

    service.close_storage()


def test_knowledge_multiple_problems_with_submissions():
    """Multiple problems with submissions should show language diversity."""
    service = CodeMemoryService(db_path=":memory:")

    # Problem 1 - Python
    p1 = Problem(title="Two Sum", slug="two-sum-multi", difficulty=DifficultyLevel.EASY, topics=["Array"])
    sub1 = Submission(
        problem_id=p1.id,
        code="def twoSum(): pass",
        language="python",
        status=SubmissionStatus.ACCEPTED
    )
    attempt1 = Attempt(problem_id=p1.id, attempt_number=1, approach_summary="Hash Map")
    attempt1.submissions.append(sub1)
    p1.attempts.append(attempt1)
    service.storage.save(p1)

    # Problem 2 - Java
    p2 = Problem(title="3Sum", slug="3sum", difficulty=DifficultyLevel.MEDIUM, topics=["Array", "Two Pointers"])
    sub2 = Submission(
        problem_id=p2.id,
        code="class Solution {}",
        language="java",
        status=SubmissionStatus.ACCEPTED
    )
    attempt2 = Attempt(problem_id=p2.id, attempt_number=1, approach_summary="Two Pointers")
    attempt2.submissions.append(sub2)
    p2.attempts.append(attempt2)
    service.storage.save(p2)

    app = create_app(service=service)
    app.dependency_overrides[get_service] = lambda: service
    with TestClient(app) as client:
        response = client.get("/api/v1/knowledge")
        assert response.status_code == 200
        data = response.json()

        entity_counts = data["entityCounts"]
        assert entity_counts["Problem"] == 2
        assert entity_counts["Language"] >= 1  # At least Python and Java
        assert entity_counts["Topic"] >= 1  # At least Array

    service.close_storage()