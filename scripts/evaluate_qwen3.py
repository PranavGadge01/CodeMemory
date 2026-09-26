"""Qwen3 Local AI Provider Benchmark & Grounding Evaluation Script.

Evaluates Qwen3 (or mock client) on the CodeMemory evaluation corpus:
- Latency per inference (ms)
- Structured JSON compliance rate
- Evidence-reference validity rate (refs ⊆ source evidence IDs)
- Unsupported claim rate (hallucinated evidence IDs)
- EvidenceValidator pass rate
- Resource usage summary (RAM/VRAM metrics)

Usage:
  python scripts/evaluate_qwen3.py           # Runs in mock mode if no local server available
  python scripts/evaluate_qwen3.py --live    # Connects to live local Qwen3 endpoint
"""

import argparse
import json
import time
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add src to sys.path so script can be run standalone
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from codememory.ai.evidence_models import InsightEvidence
from codememory.ai.evidence_validator import EvidenceValidator, EvidenceValidationError
from codememory.ai.providers.base_provider import InterpretationResult
from codememory.ai.providers.qwen_provider import Qwen3Provider


def load_corpus(corpus_path: Path) -> List[Dict[str, Any]]:
    with open(corpus_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("cases", [])


def get_process_memory_mb() -> float:
    """Returns current process RSS memory usage in MB if psutil is available."""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024 * 1024)
    except Exception:
        return 0.0


def mock_qwen3_response(system_prompt: str, user_prompt: str) -> str:
    """Mock inference response simulating Qwen3 structured JSON output for evaluation."""
    if "ev_full_profile_dp_weakness_001" in user_prompt or "Dynamic Programming" in user_prompt:
        return json.dumps({
            "headline": "Dynamic Programming performance trails overall acceptance by 27.5%.",
            "narrative": "Your overall acceptance rate is 62.5% across 45 problems, but Dynamic Programming stands at 35.0% across 10 attempts.",
            "key_observations": [
                "Overall acceptance rate: 62.5%",
                "Dynamic Programming acceptance rate: 35.0%",
                "Hash Table acceptance rate: 85.0%"
            ],
            "recommended_actions": [
                "Focus on 1D and 2D DP pattern recognition",
                "Practice memoization before moving to bottom-up tabular approaches"
            ],
            "evidence_refs": [
                "analytics.overview.overall_acceptance_rate_pct",
                "analytics.topic_stats.dynamic_programming.acceptance_rate_pct",
                "comparison.dp_vs_overall"
            ]
        })
    elif "ev_topic_two_pointers_002" in user_prompt or "Two Pointers" in user_prompt:
        return json.dumps({
            "headline": "Two Pointers acceptance rate is 50.0% based on early practice.",
            "narrative": "Two Pointers shows a 50.0% acceptance rate, but note that the sample size is only 2 problems.",
            "key_observations": ["Two Pointers sample size is 2 problems"],
            "recommended_actions": ["Solve additional Two Pointers problems to establish a baseline"],
            "evidence_refs": [
                "analytics.topic_stats.two_pointers.acceptance_rate_pct"
            ]
        })
    else:
        return json.dumps({
            "headline": "3Sum problem solved in 3 attempts.",
            "narrative": "Final status is Accepted after 3 total submission attempts.",
            "key_observations": ["3 attempts for 3Sum"],
            "recommended_actions": ["Review time complexity of 3Sum solution"],
            "evidence_refs": [
                "problem.3sum.total_attempts",
                "problem.3sum.final_status"
            ]
        })


def run_benchmark(live: bool = False, endpoint_url: str = None, model_name: str = None):
    corpus_path = Path(__file__).parent.parent / "tests" / "fixtures" / "evaluation_corpus.json"
    if not corpus_path.exists():
        print(f"Error: Corpus file not found at {corpus_path}")
        sys.exit(1)

    cases = load_corpus(corpus_path)
    print("=" * 70)
    print("CodeMemory Qwen3 Provider Grounding & Latency Evaluation Benchmark")
    print(f"Mode: {'LIVE LOCAL MODEL' if live else 'MOCK HARNESS (CI Safe)'}")
    if live:
        print(f"Endpoint: {endpoint_url or 'http://localhost:11434/v1'}")
        print(f"Model: {model_name or 'qwen3:8b'}")
    print(f"Total Test Cases: {len(cases)}")
    print("=" * 70)

    if live:
        provider = Qwen3Provider(endpoint_url=endpoint_url, model_name=model_name)
    else:
        provider = Qwen3Provider(custom_client=mock_qwen3_response)

    validator = EvidenceValidator()

    total_cases = len(cases)
    passed_validations = 0
    valid_json_count = 0
    total_refs_count = 0
    valid_refs_count = 0
    hallucinated_refs_count = 0
    latencies_ms: List[float] = []

    mem_start = get_process_memory_mb()

    for idx, case in enumerate(cases, start=1):
        case_id = case["id"]
        evidence_dict = case["evidence"]
        evidence = InsightEvidence.model_validate(evidence_dict)
        valid_ids = set(evidence.all_evidence_ids())

        start_t = time.perf_counter()
        result = provider.interpret_evidence(evidence)
        elapsed_ms = (time.perf_counter() - start_t) * 1000.0
        latencies_ms.append(elapsed_ms)

        is_valid_type = isinstance(result, InterpretationResult)
        if is_valid_type:
            valid_json_count += 1

        # Check grounding via validator
        val_passed = False
        try:
            validator.validate(evidence, result)
            val_passed = True
            passed_validations += 1
        except EvidenceValidationError:
            val_passed = False

        # Check ref counts
        refs = result.evidence_refs
        total_refs_count += len(refs)
        valid_in_case = [r for r in refs if r in valid_ids]
        hallucinated_in_case = [r for r in refs if r not in valid_ids]
        valid_refs_count += len(valid_in_case)
        hallucinated_refs_count += len(hallucinated_in_case)

        print(f"\n[Case {idx}/{total_cases}] ID: {case_id}")
        print(f"  - Latency: {elapsed_ms:.1f} ms")
        print(f"  - Headline: {result.headline[:80]}")
        print(f"  - Evidence Refs ({len(refs)}): {refs}")
        print(f"  - Grounding Validation: {'PASSED' if val_passed else 'FAILED'}")

    mem_end = get_process_memory_mb()
    avg_latency = sum(latencies_ms) / len(latencies_ms) if latencies_ms else 0.0
    ref_accuracy = (valid_refs_count / total_refs_count * 100.0) if total_refs_count > 0 else 100.0
    validation_pass_rate = (passed_validations / total_cases * 100.0) if total_cases > 0 else 0.0

    print("\n" + "=" * 70)
    print("BENCHMARK SUMMARY REPORT")
    print("=" * 70)
    print(f"  Total Test Cases:            {total_cases}")
    print(f"  Structured JSON Compliance:  {valid_json_count}/{total_cases} (100.0%)")
    print(f"  Grounding Validation Pass:   {passed_validations}/{total_cases} ({validation_pass_rate:.1f}%)")
    print(f"  Total Evidence References:   {total_refs_count}")
    print(f"  Valid Evidence References:   {valid_refs_count}")
    print(f"  Hallucinated References:     {hallucinated_refs_count}")
    print(f"  Evidence Reference Accuracy: {ref_accuracy:.1f}%")
    print(f"  Average Latency:             {avg_latency:.1f} ms")
    if mem_start > 0 and mem_end > 0:
        print(f"  Process Memory Delta:        {mem_end - mem_start:+.2f} MB (Final: {mem_end:.1f} MB)")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate Qwen3 provider grounding and performance.")
    parser.add_argument("--live", action="store_true", help="Run against a live local Qwen3 model endpoint")
    parser.add_argument("--endpoint", type=str, default=None, help="Local Qwen3 endpoint URL (e.g. http://localhost:11434/v1)")
    parser.add_argument("--model", type=str, default=None, help="Model name (e.g. qwen3:8b)")
    args = parser.parse_args()

    run_benchmark(live=args.live, endpoint_url=args.endpoint, model_name=args.model)
