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
    """Empty database should return empty clusters."""
    response = empty_client.get("/api/v1/knowledge")
    assert response.status_code == 200
    data = response.json()
    assert "graph" in data
    assert "clusters" in data
    assert data["clusters"] == []


def test_knowledge_clusters_for_shared_topics(cluster_client):
    """Problems with shared topics should form clusters."""
    response = cluster_client.get("/api/v1/knowledge")
    assert response.status_code == 200
    data = response.json()

    clusters = data["clusters"]
    assert len(clusters) > 0

    # "Array" topic should have a cluster with both Two Sum and 3Sum
    array_cluster = next((c for c in clusters if c["topicId"] == "Array"), None)
    assert array_cluster is not None, "Expected an 'Array' cluster"
    assert len(array_cluster["problemIds"]) == 2
    assert array_cluster["masteryPct"] == 0  # No submissions, so 0% mastery


def test_knowledge_clusters_deterministic(cluster_client):
    """Repeated calls should return the same cluster ordering."""
    response1 = cluster_client.get("/api/v1/knowledge")
    response2 = cluster_client.get("/api/v1/knowledge")

    assert response1.status_code == 200
    assert response2.status_code == 200

    clusters1 = response1.json()["clusters"]
    clusters2 = response2.json()["clusters"]

    # Same number of clusters
    assert len(clusters1) == len(clusters2)

    # Same cluster IDs in same order
    ids1 = [c["id"] for c in clusters1]
    ids2 = [c["id"] for c in clusters2]
    assert ids1 == ids2


def test_knowledge_cluster_mastery(cluster_client):
    """Clusters should report mastery percentage based on solved problems."""
    response = cluster_client.get("/api/v1/knowledge")
    assert response.status_code == 200
    data = response.json()

    design_cluster = next((c for c in data["clusters"] if c["topicId"] == "Design"), None)
    assert design_cluster is not None
    # One problem with "Design" topic, no submissions -> 0% mastery
    assert design_cluster["masteryPct"] == 0
    assert len(design_cluster["problemIds"]) == 1


def test_knowledge_clusters_separate_topics(cluster_client):
    """Different topics should produce separate clusters."""
    response = cluster_client.get("/api/v1/knowledge")
    assert response.status_code == 200
    data = response.json()

    cluster_topics = {c["topicId"] for c in data["clusters"]}
    # We expect Array, Hash Table, Two Pointers, and Design clusters
    # (no submissions, so all mastery is 0%)
    assert "Array" in cluster_topics
    assert "Hash Table" in cluster_topics
    assert "Two Pointers" in cluster_topics
    assert "Design" in cluster_topics

    # Array should contain both Two Sum and 3Sum
    array_cluster = next(c for c in data["clusters"] if c["topicId"] == "Array")
    assert len(array_cluster["problemIds"]) == 2

    # Design should contain only LRU Cache
    design_cluster = next(c for c in data["clusters"] if c["topicId"] == "Design")
    assert len(design_cluster["problemIds"]) == 1


def test_knowledge_graph_still_present(cluster_client):
    """The knowledge graph should still be returned alongside clusters."""
    response = cluster_client.get("/api/v1/knowledge")
    assert response.status_code == 200
    data = response.json()

    graph = data["graph"]
    assert "nodes" in graph
    assert "edges" in graph
    assert len(graph["nodes"]) > 0
    assert len(graph["edges"]) > 0
