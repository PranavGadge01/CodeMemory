"""Manual Smoke Test for Live Qwen3 Local Model Integration.

Prerequisites:
  A local OpenAI-compatible inference server running Qwen3 (e.g., Ollama, llama.cpp server, LM Studio).

Example:
  ollama run qwen3:8b
  python scripts/smoke_test_qwen3.py --endpoint http://localhost:11434/v1 --model qwen3:8b

Exits with 0 if live model produces valid, grounded insight output.
Exits with 1 on connection error or validation failure.
"""

import argparse
import sys
import time
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from codememory.ai.evidence_models import (
    EvidenceComparison,
    EvidenceItem,
    InsightEvidence,
)
from codememory.ai.evidence_validator import EvidenceValidator, EvidenceValidationError
from codememory.ai.providers.base_provider import InterpretationResult
from codememory.ai.providers.qwen_provider import Qwen3Provider


def main():
    parser = argparse.ArgumentParser(description="Smoke test live local Qwen3 model integration.")
    parser.add_argument("--endpoint", type=str, default="http://localhost:11434/v1", help="Local server OpenAI-compatible endpoint URL")
    parser.add_argument("--model", type=str, default="qwen3:8b", help="Local Qwen3 model identifier")
    args = parser.parse_args()

    print("=" * 65)
    print("CodeMemory Qwen3 Live Local Smoke Test")
    print(f"Target Endpoint: {args.endpoint}")
    print(f"Target Model:    {args.model}")
    print("=" * 65)

    evidence = InsightEvidence(
        scope="full_profile",
        items=[
            EvidenceItem(
                evidence_id="analytics.overview.overall_acceptance_rate_pct",
                source="analytics.overview",
                label="Overall Acceptance Rate",
                value=60.0,
                unit="%",
            ),
            EvidenceItem(
                evidence_id="analytics.topic_stats.sliding_window.acceptance_rate_pct",
                source="analytics.topic_stats.sliding_window",
                label="Sliding Window Acceptance Rate",
                value=40.0,
                unit="%",
                sample_size=5,
            ),
        ],
        comparisons=[
            EvidenceComparison(
                evidence_id="comparison.sliding_window_vs_overall",
                topic_evidence_id="analytics.topic_stats.sliding_window.acceptance_rate_pct",
                overall_evidence_id="analytics.overview.overall_acceptance_rate_pct",
                topic_rate=40.0,
                overall_rate=60.0,
                delta=-20.0,
                label="Sliding Window vs Overall",
            )
        ],
    )

    provider = Qwen3Provider(endpoint_url=args.endpoint, model_name=args.model)

    print("\nSending evidence bundle to local Qwen3 model...")
    t0 = time.perf_counter()
    try:
        result = provider.interpret_evidence(evidence)
        elapsed_sec = time.perf_counter() - t0
    except Exception as e:
        print(f"\n[FAIL] Request to local Qwen3 model failed: {e}")
        sys.exit(1)

    print(f"\n[SUCCESS] Response received in {elapsed_sec:.2f} seconds.")
    print("-" * 65)
    print(f"Headline: {result.headline}")
    print(f"\nNarrative:\n{result.narrative}")
    print(f"\nKey Observations:\n  " + "\n  ".join(f"- {o}" for o in result.key_observations))
    print(f"\nRecommended Actions:\n  " + "\n  ".join(f"- {a}" for a in result.recommended_actions))
    print(f"\nEvidence Refs: {result.evidence_refs}")
    print("-" * 65)

    # Validate evidence provenance
    validator = EvidenceValidator()
    try:
        validator.validate(evidence, result)
        print("\n[GROUNDING CHECK] EvidenceValidator PASSED: All evidence_refs exist in source evidence.")
    except EvidenceValidationError as e:
        print(f"\n[GROUNDING WARNING] EvidenceValidator issue: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
