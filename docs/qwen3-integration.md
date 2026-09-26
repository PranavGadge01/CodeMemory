# Qwen3 Local AI Provider Integration Guide

This guide details the setup, configuration, fallback mechanisms, grounding validation, and benchmarking procedures for CodeMemory's local **Qwen3** AI Provider (`Qwen3Provider`).

---

## 1. Overview & Architectural Boundaries

CodeMemory's grounded personalized insight pipeline maintains a strict deterministic architecture:

```
LeetCode/Submissions
        │
        ▼
Deterministic Analytics (AnalyticsService & PatternAnalyzer)
        │
        ▼
  EvidenceBuilder
        │ (Produces InsightEvidence bundle)
        ▼
   AI Provider (Qwen3Provider / OpenAIProvider / HeuristicAIProvider)
        │ (Produces InterpretationResult shape)
        ▼
  EvidenceValidator
        │ (Enforces evidence_refs ⊆ source evidence IDs)
        ▼
   GroundedInsight
```

**Grounding Principles**:
1. **Evidence is Authoritative**: Qwen3 interprets deterministic evidence prepared by `EvidenceBuilder`. It does not query the database or calculate statistics independently.
2. **Strict Provenance**: Every metric and observation cited by Qwen3 must link back to a valid `evidence_id`. Any hallucinated IDs are automatically stripped.
3. **Provider-Agnostic Core**: `InsightService`, domain models, FastAPI routes, and CLI code remain 100% provider-agnostic.

---

## 2. Configuration & Environment Variables

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `AI_PROVIDER` | `heuristic` | Active AI provider (`qwen`, `openai`, `heuristic`) |
| `QWEN_ENDPOINT_URL` | `http://localhost:11434/v1` | OpenAI-compatible local server URL (Ollama, llama.cpp, LM Studio, etc.) |
| `QWEN_MODEL_NAME` | `qwen3:8b` | Local model tag or identifier |
| `QWEN_API_KEY` | `qwen` | Optional authorization key for local server |
| `QWEN_TIMEOUT_SECONDS`| `30.0` | Timeout in seconds for local model inference |
| `QWEN_TEMPERATURE` | `0.2` | Generation temperature for local model |
| `QWEN_MAX_TOKENS` | `2048` | Maximum output generation tokens |

---

## 3. Local Model Setup Instructions

### Option A: Ollama (Recommended)
1. Install [Ollama](https://ollama.com/).
2. Run Qwen3:
   ```bash
   ollama run qwen3:8b
   ```
3. Set environment variables in your `.env` file:
   ```env
   AI_PROVIDER=qwen
   QWEN_ENDPOINT_URL=http://localhost:11434/v1
   QWEN_MODEL_NAME=qwen3:8b
   ```

### Option B: llama.cpp Server / LM Studio
1. Start `llama-server` or LM Studio with OpenAI compatibility enabled on `http://localhost:8080/v1`.
2. Set environment variables:
   ```env
   AI_PROVIDER=qwen
   QWEN_ENDPOINT_URL=http://localhost:8080/v1
   QWEN_MODEL_NAME=qwen3-8b-instruct
   ```

---

## 4. Failure & Fallback Behavior

`Qwen3Provider` automatically falls back to `HeuristicAIProvider` under any of the following conditions:
- Local server is offline or connection is refused.
- Inference times out (`QWEN_TIMEOUT_SECONDS`).
- Model output cannot be parsed as valid JSON or markdown-fenced JSON.
- Output fails Pydantic schema validation (`InterpretationResult`, `SubmissionAnalysis`, `SolutionEvolution`).

Fallback ensures CodeMemory is **always functional** even when offline or when local model resources are unavailable.

---

## 5. Benchmarking & Grounding Evaluation

A versioned evaluation benchmark corpus is provided in `tests/fixtures/evaluation_corpus.json`.

### Run Benchmark with Mock Harness (CI Safe)
```bash
python scripts/evaluate_qwen3.py
```

### Run Benchmark Against Live Local Model Endpoint
```bash
python scripts/evaluate_qwen3.py --live --endpoint http://localhost:11434/v1 --model qwen3:8b
```

### Manual Live Smoke Test
```bash
python scripts/smoke_test_qwen3.py --endpoint http://localhost:11434/v1 --model qwen3:8b
```

---

## 6. Unit Testing in CI

CI test execution remains **100% GPU-free and model-free**:
- `tests/test_qwen_provider.py` uses an injected fake client harness to test JSON parsing, markdown block extraction, hallucinated ref filtering, timeout fallbacks, and `EvidenceValidator` pipeline integration.
