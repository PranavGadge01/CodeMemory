"""Unit and integration tests for Qwen3Provider local AI provider integration."""

import json
from unittest.mock import MagicMock, patch
import pytest

from codememory.ai.evidence_builder import EvidenceBuilder
from codememory.ai.evidence_models import (
    EvidenceComparison,
    EvidenceItem,
    InsightEvidence,
    ProblemSnapshot,
)
from codememory.ai.evidence_validator import EvidenceValidator
from codememory.ai.insight_service import GroundedInsight, InsightService
from codememory.ai.models import SolutionEvolution, SubmissionAnalysis
from codememory.ai.providers import (
    BaseAIProvider,
    HeuristicAIProvider,
    OpenAIProvider,
    Qwen3Provider,
    get_ai_provider,
)
from codememory.ai.providers.base_provider import InterpretationResult
from codememory.domain.enums import DifficultyLevel, SubmissionStatus
from codememory.domain.models import Problem, Submission


@pytest.fixture
def sample_evidence():
    return InsightEvidence(
        scope="full_profile",
        items=[
            EvidenceItem(
                evidence_id="analytics.overview.overall_acceptance_rate_pct",
                source="analytics.overview",
                label="Overall Acceptance Rate",
                value=58.0,
                unit="%",
            ),
            EvidenceItem(
                evidence_id="analytics.topic_stats.dynamic_programming.acceptance_rate_pct",
                source="analytics.topic_stats.dynamic_programming",
                label="Dynamic Programming Acceptance Rate",
                value=42.0,
                unit="%",
                sample_size=12,
            ),
        ],
        comparisons=[
            EvidenceComparison(
                evidence_id="comparison.dynamic_programming_vs_overall",
                topic_evidence_id="analytics.topic_stats.dynamic_programming.acceptance_rate_pct",
                overall_evidence_id="analytics.overview.overall_acceptance_rate_pct",
                topic_rate=42.0,
                overall_rate=58.0,
                delta=-16.0,
                label="Dynamic Programming vs Overall",
            )
        ],
    )


class TestQwen3ProviderContract:
    def test_provider_factory(self, monkeypatch):
        monkeypatch.setenv("AI_PROVIDER", "qwen")
        provider = get_ai_provider()
        assert isinstance(provider, Qwen3Provider)

    def test_satisfies_base_ai_provider_interface(self):
        provider = Qwen3Provider()
        assert isinstance(provider, BaseAIProvider)

    def test_interpret_evidence_valid_json(self, sample_evidence):
        def fake_client(system_prompt, user_prompt):
            return json.dumps({
                "headline": "DP acceptance rate is significantly below average.",
                "narrative": "Dynamic Programming shows a 42.0% acceptance rate compared to overall 58.0%.",
                "key_observations": ["DP acceptance is 16.0% below average"],
                "recommended_actions": ["Practice DP memoization patterns"],
                "evidence_refs": ["analytics.topic_stats.dynamic_programming.acceptance_rate_pct", "comparison.dynamic_programming_vs_overall"]
            })

        provider = Qwen3Provider(custom_client=fake_client)
        result = provider.interpret_evidence(sample_evidence)

        assert isinstance(result, InterpretationResult)
        assert result.headline == "DP acceptance rate is significantly below average."
        assert "analytics.topic_stats.dynamic_programming.acceptance_rate_pct" in result.evidence_refs

    def test_interpret_evidence_handles_markdown_code_fences(self, sample_evidence):
        def fake_client(system_prompt, user_prompt):
            return """```json
{
    "headline": "Structured insight from Qwen3.",
    "narrative": "Explanation narrative here.",
    "key_observations": ["Obs 1"],
    "recommended_actions": ["Action 1"],
    "evidence_refs": ["analytics.overview.overall_acceptance_rate_pct"]
}
```"""

        provider = Qwen3Provider(custom_client=fake_client)
        result = provider.interpret_evidence(sample_evidence)

        assert isinstance(result, InterpretationResult)
        assert result.headline == "Structured insight from Qwen3."
        assert "analytics.overview.overall_acceptance_rate_pct" in result.evidence_refs

    def test_interpret_evidence_filters_hallucinated_refs(self, sample_evidence):
        def fake_client(system_prompt, user_prompt):
            return json.dumps({
                "headline": "Insight with hallucinated reference.",
                "narrative": "Narrative here.",
                "key_observations": [],
                "recommended_actions": [],
                "evidence_refs": ["analytics.overview.overall_acceptance_rate_pct", "fake_evidence_999"]
            })

        provider = Qwen3Provider(custom_client=fake_client)
        result = provider.interpret_evidence(sample_evidence)

        assert isinstance(result, InterpretationResult)
        assert "analytics.overview.overall_acceptance_rate_pct" in result.evidence_refs
        assert "fake_evidence_999" not in result.evidence_refs

    def test_fallback_on_malformed_json(self, sample_evidence):
        def fake_client(system_prompt, user_prompt):
            return "This is raw prose with no JSON at all."

        provider = Qwen3Provider(custom_client=fake_client)
        result = provider.interpret_evidence(sample_evidence)

        # Must gracefully degrade to HeuristicAIProvider result
        assert isinstance(result, InterpretationResult)
        assert len(result.headline) > 0

    def test_fallback_on_runtime_error(self, sample_evidence):
        def fake_client(system_prompt, user_prompt):
            raise RuntimeError("Connection refused by local server")

        provider = Qwen3Provider(custom_client=fake_client)
        result = provider.interpret_evidence(sample_evidence)

        assert isinstance(result, InterpretationResult)
        assert len(result.headline) > 0

    def test_analyze_submission_valid(self):
        def fake_client(system_prompt, user_prompt):
            return json.dumps({
                "approach": "Two Pointers",
                "algorithms": ["Two Pointers"],
                "data_structures": ["Array"],
                "inferred_pattern": "Two Pointers",
                "time_complexity": "O(n)",
                "space_complexity": "O(1)",
                "correctness_summary": "Accepted solution",
                "concise_explanation": "Iterates from both ends",
                "certain_facts": ["O(n) time complexity"],
                "likely_explanations": [],
                "analysis_version": "v1"
            })

        problem = Problem(id="two-sum", title="Two Sum", difficulty=DifficultyLevel.EASY)
        submission = Submission(id="sub-1", problem_id="two-sum", status=SubmissionStatus.ACCEPTED, language="python", code="def twoSum(): pass")

        provider = Qwen3Provider(custom_client=fake_client)
        analysis = provider.analyze_submission(submission, problem)

        assert isinstance(analysis, SubmissionAnalysis)
        assert analysis.approach == "Two Pointers"

    def test_analyze_submission_fallback(self):
        def fake_client(system_prompt, user_prompt):
            raise TimeoutError("Model request timed out")

        problem = Problem(id="two-sum", title="Two Sum", difficulty=DifficultyLevel.EASY)
        submission = Submission(id="sub-1", problem_id="two-sum", status=SubmissionStatus.ACCEPTED, language="python", code="def twoSum(): pass")

        provider = Qwen3Provider(custom_client=fake_client)
        analysis = provider.analyze_submission(submission, problem)

        assert isinstance(analysis, SubmissionAnalysis)

    def test_answer_question(self):
        def fake_client(system_prompt, user_prompt):
            return "Based on your history with Two Sum, your primary pattern was Hash Table."

        provider = Qwen3Provider(custom_client=fake_client)
        answer = provider.answer_question("What pattern did I use for Two Sum?", "Context: Two Sum (Accepted)")

        assert "Two Sum" in answer


class TestE2EGroundedInsightWithQwen3:
    def test_end_to_end_pipeline(self, sample_evidence):
        def fake_client(system_prompt, user_prompt):
            return json.dumps({
                "headline": "DP requires focused practice.",
                "narrative": "DP acceptance rate is 42.0%, trailing your overall rate of 58.0%.",
                "key_observations": ["DP rate lower than overall"],
                "recommended_actions": ["Review classic DP problems"],
                "evidence_refs": ["analytics.topic_stats.dynamic_programming.acceptance_rate_pct"]
            })

        provider = Qwen3Provider(custom_client=fake_client)

        builder = MagicMock()
        builder.build_full_profile_evidence.return_value = sample_evidence

        service = InsightService(ai_provider=provider, evidence_builder=builder)
        insight = service.generate_full_profile_insight()

        assert isinstance(insight, GroundedInsight)
        assert insight.headline == "DP requires focused practice."
        assert "analytics.topic_stats.dynamic_programming.acceptance_rate_pct" in insight.evidence_refs

    def test_ai_enabled_disabled_triggers_heuristic_fallback(self, sample_evidence, monkeypatch):
        monkeypatch.setenv("AI_ENABLED", "false")
        client_called = False

        def fake_client(system_prompt, user_prompt):
            nonlocal client_called
            client_called = True
            return "{}"

        provider = Qwen3Provider(custom_client=fake_client)
        result = provider.interpret_evidence(sample_evidence)

        assert client_called is False
        assert isinstance(result, InterpretationResult)
        assert len(result.headline) > 0

    def test_timeout_handling_triggers_observable_fallback(self, sample_evidence):
        def fake_client(system_prompt, user_prompt):
            raise TimeoutError("Qwen3 inference server timed out after 30s")

        provider = Qwen3Provider(custom_client=fake_client)
        result = provider.interpret_evidence(sample_evidence)

        assert isinstance(result, InterpretationResult)
        assert len(result.headline) > 0

    def test_adversarial_valid_and_invalid_refs_sanitized(self, sample_evidence):
        def fake_client(system_prompt, user_prompt):
            return json.dumps({
                "headline": "Adversarial test with bogus refs",
                "narrative": "Claiming 99% accuracy on non-existent topic",
                "key_observations": ["Bogus claim"],
                "recommended_actions": [],
                "evidence_refs": [
                    "analytics.overview.overall_acceptance_rate_pct",  # valid
                    "fake_ref_unsupported_1",                          # invalid
                    "fake_ref_unsupported_2"                           # invalid
                ]
            })

        provider = Qwen3Provider(custom_client=fake_client)
        builder = MagicMock()
        builder.build_full_profile_evidence.return_value = sample_evidence

        service = InsightService(ai_provider=provider, evidence_builder=builder)
        insight = service.generate_full_profile_insight()

        assert isinstance(insight, GroundedInsight)
        # Invalid refs must be filtered out before InsightService validation
        assert "analytics.overview.overall_acceptance_rate_pct" in insight.evidence_refs
        assert "fake_ref_unsupported_1" not in insight.evidence_refs

    def test_configuration_custom_settings(self, monkeypatch):
        monkeypatch.setenv("QWEN_ENDPOINT_URL", "http://localhost:8080/v1")
        monkeypatch.setenv("QWEN_MODEL_NAME", "qwen3-coder-14b-instruct")
        monkeypatch.setenv("QWEN_TIMEOUT_SECONDS", "45")
        monkeypatch.setenv("QWEN_TEMPERATURE", "0.1")
        monkeypatch.setenv("QWEN_MAX_TOKENS", "1024")

        provider = Qwen3Provider()
        assert provider.endpoint_url == "http://localhost:8080/v1"
        assert provider.model_name == "qwen3-coder-14b-instruct"
        assert provider.timeout_seconds == 45.0
        assert provider.temperature == 0.1
        assert provider.max_tokens == 1024

    def test_secrets_scrubbed_in_logs(self, sample_evidence):
        secret_key = "sk-secret-qwen-key-999"
        provider = Qwen3Provider(api_key=secret_key)
        e = Exception(f"Failed connecting with key {secret_key}")

        sanitized = provider._sanitize_error(e)
        assert secret_key not in sanitized
        assert "[REDACTED_API_KEY]" in sanitized

    def test_no_network_requests_on_construction(self, monkeypatch):
        network_called = False

        def mock_urlopen(*args, **kwargs):
            nonlocal network_called
            network_called = True
            raise RuntimeError("Network should not be called on construction")

        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)
        provider = Qwen3Provider()

        assert provider is not None
        assert network_called is False

    def test_existing_providers_contracts_unaffected(self, sample_evidence):
        heuristic = HeuristicAIProvider()
        result_h = heuristic.interpret_evidence(sample_evidence)
        assert isinstance(result_h, InterpretationResult)
        assert len(result_h.headline) > 0

        openai_p = OpenAIProvider(api_key="")  # Disabled / no key
        result_o = openai_p.interpret_evidence(sample_evidence)
        assert isinstance(result_o, InterpretationResult)
        assert len(result_o.headline) > 0


