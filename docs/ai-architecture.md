# CodeMemory Phase 6: AI Architecture & Solution Evolution

CodeMemory integrates an optional, local-first AI intelligence layer that analyzes the user's **ACTUAL** submission attempts and historical solving evolution.

> ⚠️ **Core Principle**: CodeMemory is **NOT** an AI chatbot wrapper. The core product remains a personal DSA knowledge engine. The user's actual submission history is always the single source of truth. AI operates purely as an analytical enhancement layer over stored historical data.

---

## 1. Provider Abstraction Architecture

The AI layer is built around a pluggable provider interface (`BaseAIProvider`):

```
                     BaseAIProvider (Abstract Interface)
                                │
       ┌────────────────────────┼────────────────────────┐
       ▼                        ▼                        ▼
 Qwen3Provider            OpenAIProvider           HeuristicAIProvider
(Local Qwen3 Model,      (Cloud OpenAI API,       (Deterministic Rule/Regex AST,
 OpenAI-Compatible)       Structured Pydantic)      Offline Fallback Default)
```

- **`BaseAIProvider`**: Defines methods for single submission analysis (`analyze_submission`), solution evolution analysis (`analyze_evolution`), grounded QA (`answer_question`), and structured evidence interpretation (`interpret_evidence`).
- **`Qwen3Provider`**: Local-first provider communicating with an OpenAI-compatible local model server (e.g. Ollama, llama.cpp server, LM Studio) hosting a quantized Qwen3 model.
- **`HeuristicAIProvider`**: Deterministic rule-based provider for offline use without requiring external API keys or local AI model servers.
- **`OpenAIProvider`**: API-backed cloud provider utilizing structured JSON output mode with strict Pydantic validation.

Select the provider by setting `AI_PROVIDER=qwen`, `AI_PROVIDER=openai`, or `AI_PROVIDER=heuristic`. If no key or local server is set, CodeMemory operates seamlessly in offline mode using `HeuristicAIProvider`.

---

## 2. Deterministic Caching & Versioning

To avoid redundant API calls and control costs:
- **Analysis Identity Key**: `(submission_id, code_hash, analysis_version)`
  - `code_hash` is computed as `SHA-256(submission_id + code + status)`.
- **Version Tracking**: Prompts and schemas carry an `analysis_version` string (e.g. `"v1"`).
- **Caching Behavior**:
  - Re-analyzing the same code under the same version returns the cached analysis instantly.
  - Modifying the code or incrementing the prompt version triggers a fresh AI analysis.

Cache records are persisted to `data/ai_analyses.parquet` and `data/evolution_analyses.parquet`.

---

## 3. Structured Output Schemas

AI output is strictly validated against Pydantic models:

### `SubmissionAnalysis`
- `approach`: Inferred algorithmic approach or design pattern.
- `algorithms`: List of primary algorithms present.
- `data_structures`: List of primary data structures present.
- `inferred_pattern`: Main problem-solving pattern.
- `time_complexity` / `space_complexity`: Big-O complexities.
- `certain_facts`: Empirical facts directly observable from code and metadata (e.g. loop count, runtime).
- `likely_explanations`: Hypothesized reasons for failure (e.g. TLE, WA edge cases).
- `concise_explanation`: Summary explanation of the code design.

### `SolutionEvolution`
- `initial_approach` vs `final_approach`
- `major_changes`: Strategic algorithmic transitions.
- `optimization_steps`: Time/space complexity improvements.
- `mistakes_identified` & `learning_points`: Key takeaways across attempt sequence.

---

## 4. Grounded Question Answering ("Ask CodeMemory")

The "Ask CodeMemory" feature allows users to query their personal DSA history in natural language:
- **Retrieval**: Relevant problem records are searched and selected based on query intent.
- **`ContextBuilder`**: Assembles a bounded, token-limited context string containing the user's actual attempts and notes.
- **Grounded AI Synthesis**: The AI synthesizes an answer based **strictly** on the retrieved context, citing specific problem titles and attempt numbers.
- **No Hallucination**: If no matching records exist in the user's database, the system explicitly reports that no relevant historical records were found.

---

## 5. Privacy & Data Boundaries

1. **Explicit API Warnings**: External API calls are made only when explicitly configured by the user.
2. **Zero Credential Logging**: API keys and tokens are never logged or stored in analysis outputs.
3. **Immutability of Source Truth**: AI analyses are stored separately and **NEVER** overwrite original user source code, runtime, memory, or submission timestamps.
