"""Tests for the explainable AI learning API endpoints.

Covers:
  - GET /api/v1/problems/{slug}/learning-analysis
  - GET /api/v1/problems/{slug}/optimization
  - GET /api/v1/learning/patterns
  - GET /api/v1/learning/recommendations
  - GET /api/v1/learning/roadmap
"""

import pytest


# ─── Learning Analysis ───────────────────────────────────────────────────────

class TestLearningAnalysis:
    def test_returns_200_for_existing_problem(self, client):
        response = client.get("/api/v1/problems/two-sum/learning-analysis")
        assert response.status_code == 200
        data = response.json()
        assert data["problem_slug"] == "two-sum"
        assert "problem_title" in data
        assert isinstance(data["timeline"], list)
        assert isinstance(data["improvements"], list)
        assert isinstance(data["regressions"], list)
        assert isinstance(data["unresolved_issues"], list)
        assert "learning_summary" in data
        assert "recommended_next_action" in data
        assert isinstance(data["evidence_refs"], list)

    def test_returns_404_for_missing_problem(self, client):
        response = client.get("/api/v1/problems/non-existent-xyz/learning-analysis")
        assert response.status_code == 404

    def test_returns_400_for_empty_slug(self, client):
        # URL-encoded space — slug is whitespace only
        response = client.get("/api/v1/problems/%20/learning-analysis")
        # Either 404 (treated as unknown slug) or 400 is acceptable
        assert response.status_code in (400, 404)

    def test_timeline_entries_have_expected_shape(self, client):
        response = client.get("/api/v1/problems/two-sum/learning-analysis")
        assert response.status_code == 200
        for entry in response.json()["timeline"]:
            assert "attempt" in entry
            assert "submission_id" in entry
            assert "status" in entry
            assert "language" in entry


# ─── Optimization Explanation ─────────────────────────────────────────────────

class TestOptimizationExplanation:
    def test_returns_200_for_existing_problem(self, client):
        response = client.get("/api/v1/problems/two-sum/optimization")
        assert response.status_code == 200
        data = response.json()
        assert data["problem_slug"] == "two-sum"
        assert "current_approach" in data
        assert "recommended_approach" in data
        assert "bottleneck" in data
        assert "takeaway" in data
        assert "complexity_comparison" in data
        assert isinstance(data["edge_cases"], list)
        assert isinstance(data["evidence_refs"], list)

    def test_complexity_comparison_has_required_fields(self, client):
        response = client.get("/api/v1/problems/two-sum/optimization")
        assert response.status_code == 200
        cc = response.json()["complexity_comparison"]
        assert "current_time" in cc
        assert "proposed_time" in cc
        assert "current_space" in cc
        assert "proposed_space" in cc
        assert "explanation" in cc

    def test_returns_404_for_missing_problem(self, client):
        response = client.get("/api/v1/problems/non-existent-xyz/optimization")
        assert response.status_code == 404

    def test_accepts_submission_id_query_param(self, client):
        # Should not 422 even for unknown submission_id — graceful fallback
        response = client.get("/api/v1/problems/two-sum/optimization?submission_id=does-not-exist")
        assert response.status_code == 200


# ─── Submission Patterns ──────────────────────────────────────────────────────

class TestSubmissionPatterns:
    def test_returns_200(self, client):
        response = client.get("/api/v1/learning/patterns")
        assert response.status_code == 200

    def test_response_shape(self, client):
        data = client.get("/api/v1/learning/patterns").json()
        assert "summary" in data
        assert isinstance(data["findings"], list)
        assert "most_important_gap" in data
        assert isinstance(data["evidence_refs"], list)
        assert isinstance(data["sample_size_notes"], list)

    def test_finding_shape(self, client):
        data = client.get("/api/v1/learning/patterns").json()
        for finding in data["findings"]:
            assert "title" in finding
            assert "observation" in finding
            assert "category" in finding
            assert "why_it_matters" in finding
            assert "suggested_action" in finding

    def test_empty_service_still_returns_200(self, empty_client):
        response = empty_client.get("/api/v1/learning/patterns")
        assert response.status_code == 200


# ─── Next-Problem Recommendations ────────────────────────────────────────────

class TestNextRecommendations:
    def test_returns_200(self, client):
        response = client.get("/api/v1/learning/recommendations")
        assert response.status_code == 200

    def test_default_limit_is_respected(self, client):
        data = client.get("/api/v1/learning/recommendations").json()
        assert "recommendations" in data
        assert "generated_at" in data
        assert len(data["recommendations"]) <= 3

    def test_custom_limit(self, client):
        data = client.get("/api/v1/learning/recommendations?limit=1").json()
        assert len(data["recommendations"]) <= 1

    def test_limit_out_of_range_returns_422(self, client):
        response = client.get("/api/v1/learning/recommendations?limit=0")
        assert response.status_code == 422
        response = client.get("/api/v1/learning/recommendations?limit=11")
        assert response.status_code == 422

    def test_recommendation_shape(self, client):
        data = client.get("/api/v1/learning/recommendations").json()
        for rec in data["recommendations"]:
            assert "problem_slug" in rec
            assert "title" in rec
            assert "difficulty" in rec
            assert "selection_rationale" in rec
            assert "target_skill" in rec
            assert isinstance(rec["topics"], list)
            assert isinstance(rec["reflection_checklist"], list)

    def test_empty_catalog_returns_empty_list(self, empty_client):
        data = empty_client.get("/api/v1/learning/recommendations").json()
        assert data["recommendations"] == []


# ─── Personalized Roadmap ────────────────────────────────────────────────────

class TestPersonalizedRoadmap:
    def test_returns_200(self, client):
        response = client.get("/api/v1/learning/roadmap")
        assert response.status_code == 200

    def test_response_shape(self, client):
        data = client.get("/api/v1/learning/roadmap").json()
        assert "title" in data
        assert "description" in data
        assert isinstance(data["milestones"], list)
        assert "generated_at" in data
        assert "evidence_id" in data

    def test_milestones_have_required_fields(self, client):
        data = client.get("/api/v1/learning/roadmap").json()
        for m in data["milestones"]:
            assert "id" in m
            assert "title" in m
            assert "order" in m
            assert "learning_objective" in m
            assert "completion_criteria" in m
            assert "status" in m
            assert isinstance(m["recommended_problems"], list)
            assert isinstance(m["concepts_to_study"], list)
            assert isinstance(m["prerequisites"], list)

    def test_milestone_order_is_sequential(self, client):
        data = client.get("/api/v1/learning/roadmap").json()
        orders = [m["order"] for m in data["milestones"]]
        assert orders == sorted(orders)

    def test_empty_service_still_returns_200(self, empty_client):
        response = empty_client.get("/api/v1/learning/roadmap")
        assert response.status_code == 200


# ─── Collective learning profile ─────────────────────────────────────────────

class TestCollectiveLearningProfile:
    def test_profile_returns_200_with_structure(self, client):
        response = client.get("/api/v1/learning/profile")
        assert response.status_code == 200
        data = response.json()
        for key in (
            "overall_summary",
            "profile",
            "strengths",
            "weaknesses",
            "recurring_mistakes",
            "optimization_trends",
            "progress",
            "focus_areas",
            "recommended_actions",
            "limitations",
            "evidence_refs",
        ):
            assert key in data, f"missing key: {key}"
        assert isinstance(data["strengths"], list)
        assert isinstance(data["weaknesses"], list)
        assert isinstance(data["profile"]["difficulty_solved"], dict)

    def test_profile_insight_items_carry_evidence(self, client):
        data = client.get("/api/v1/learning/profile").json()
        for item in data["strengths"] + data["weaknesses"] + data["focus_areas"]:
            assert item["category"] in {"fact", "pattern", "interpretation", "action"}
            assert item["title"]
            assert item["summary"]
            assert isinstance(item["evidence_refs"], list)

    def test_empty_service_profile_is_cautious(self, empty_client):
        response = empty_client.get("/api/v1/learning/profile")
        assert response.status_code == 200
        data = response.json()
        assert data["is_early_stage"] is True
        assert data["profile"]["total_problems"] == 0
        # No fabricated strengths for an empty history.
        assert data["strengths"] == []
        assert data["weaknesses"] == []
        assert data["limitations"]


# ─── Per-submission learning analysis ────────────────────────────────────────

class TestSubmissionLearningAnalysis:
    def _submission_id(self, client):
        problems = client.get("/api/v1/problems").json()
        items = problems.get("items", problems) if isinstance(problems, dict) else problems
        slug = items[0]["slug"]
        detail = client.get(f"/api/v1/problems/{slug}").json()
        attempts = detail.get("attempts", [])
        for attempt in attempts:
            for sub in attempt.get("submissions", []):
                return sub["id"]
        raise AssertionError("no submission found")

    def test_submission_analysis_returns_200(self, client):
        submission_id = self._submission_id(client)
        response = client.get(f"/api/v1/learning/submissions/{submission_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["submission_id"] == submission_id
        for key in (
            "overview",
            "what_went_well",
            "improvements",
            "current_time_complexity",
            "complexity_source",
            "edge_cases",
            "previous_attempt_comparison",
            "lesson",
            "next_action",
        ):
            assert key in data, f"missing key: {key}"
        assert isinstance(data["what_went_well"], list)
        assert isinstance(data["improvements"], list)

    def test_missing_submission_returns_404(self, client):
        response = client.get("/api/v1/learning/submissions/does-not-exist-xyz")
        assert response.status_code == 404

    def test_empty_submission_id_returns_404_or_400(self, client):
        response = client.get("/api/v1/learning/submissions/%20")
        assert response.status_code in (400, 404)
