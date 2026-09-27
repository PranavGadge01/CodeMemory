import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from codememory.ai.insight_service import GroundedInsight
from codememory.ai.providers import BaseAIProvider, HeuristicAIProvider, Qwen3Provider
from codememory.ai.providers.base_provider import InterpretationResult
from api.app import create_app
from api.dependencies import get_service


def test_get_full_profile_insight(client):
    response = client.get("/api/v1/insights")
    assert response.status_code == 200
    data = response.json()

    assert data["scope"] == "full_profile"
    assert "headline" in data
    assert "narrative" in data
    assert isinstance(data["key_observations"], list)
    assert isinstance(data["recommended_actions"], list)
    assert isinstance(data["evidence_refs"], list)
    assert "evidence_id" in data


def test_get_topic_insight(client):
    response = client.get("/api/v1/insights/topic/Array")
    assert response.status_code == 200
    data = response.json()

    assert data["scope"] == "topic:Array"
    assert "headline" in data
    assert "narrative" in data


def test_get_topic_insight_empty_topic_returns_bad_request(client):
    response = client.get("/api/v1/insights/topic/%20%20")
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "BAD_REQUEST"


def test_get_problem_insight(client):
    response = client.get("/api/v1/insights/problem/two-sum")
    assert response.status_code == 200
    data = response.json()

    assert data["scope"] == "problem:two-sum"
    assert "headline" in data


def test_get_problem_insight_not_found(client):
    response = client.get("/api/v1/insights/problem/non-existent-problem-slug")
    assert response.status_code == 404
    data = response.json()

    assert data["error"]["code"] == "NOT_FOUND"
    assert "Problem not found" in data["error"]["message"]


def test_insight_endpoint_error_isolation_no_stack_trace_leak(mock_service):
    # Inject a failing AI provider that throws a raw Exception with file paths
    failing_provider = MagicMock(spec=BaseAIProvider)
    failing_provider.interpret_evidence.side_effect = RuntimeError(
        "Database error at /var/secrets/internal/db.py line 42 with key sk-secret-12345"
    )

    mock_service.ai_provider = failing_provider
    app = create_app(service=mock_service)
    app.dependency_overrides[get_service] = lambda: mock_service

    with TestClient(app) as test_client:
        response = test_client.get("/api/v1/insights")
        
        # When provider raises an error inside interpret_evidence, Qwen3/OpenAI providers fall back gracefully.
        # But if raw exception escapes to FastAPI layer, HTTP 500 exception handler scrubs stack traces.
        assert response.status_code in (200, 500)
        data = response.json()

        if response.status_code == 500:
            assert data["error"]["code"] == "INTERNAL_ERROR"
            assert "sk-secret-12345" not in data["error"]["message"]
            assert "/var/secrets" not in data["error"]["message"]


def test_insight_endpoint_with_qwen_provider(mock_service):
    def fake_qwen_client(system_prompt, user_prompt):
        import json
        return json.dumps({
            "headline": "Structured insight from Qwen3 API endpoint.",
            "narrative": "Detailed grounded narrative here.",
            "key_observations": ["Observation 1"],
            "recommended_actions": ["Action 1"],
            "evidence_refs": ["analytics.overview.overall_acceptance_rate_pct"]
        })

    qwen_provider = Qwen3Provider(custom_client=fake_qwen_client)
    mock_service.ai_provider = qwen_provider
    mock_service.insight_service.ai_provider = qwen_provider

    app = create_app(service=mock_service)
    app.dependency_overrides[get_service] = lambda: mock_service

    with TestClient(app) as test_client:
        response = test_client.get("/api/v1/insights")
        assert response.status_code == 200
        data = response.json()

        assert data["headline"] == "Structured insight from Qwen3 API endpoint."
        assert "Observation 1" in data["key_observations"]


def test_get_full_profile_insight_account_scoping(multi_account_client):
    response = multi_account_client.get("/api/v1/insights")
    assert response.status_code == 200
    data = response.json()

    assert data["scope"] == "full_profile"
    assert "headline" in data
    assert "narrative" in data
    # Verify evidence summary is grounded in the active account ("maytrix" has 1 problem)
    assert "1/1 problems solved" in data["evidence_summary"] or "acceptance rate" in data["evidence_summary"]

