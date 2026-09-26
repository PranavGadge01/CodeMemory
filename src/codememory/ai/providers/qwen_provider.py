"""Qwen3 local AI provider implementation with structured JSON output validation and offline fallback."""

import json
import logging
import os
from typing import Any, Callable, List, Optional
import urllib.request
import urllib.error

from pydantic import ValidationError

from codememory.ai.evidence_models import InsightEvidence
from codememory.ai.models import SolutionEvolution, SubmissionAnalysis
from codememory.ai.prompts import (
    SYSTEM_ASK_CODEMEMORY_PROMPT,
    SYSTEM_EVOLUTION_ANALYSIS_PROMPT,
    SYSTEM_INTERPRET_EVIDENCE_PROMPT,
    SYSTEM_SUBMISSION_ANALYSIS_PROMPT,
    USER_ASK_CODEMEMORY_PROMPT,
    USER_EVOLUTION_ANALYSIS_PROMPT,
    USER_INTERPRET_EVIDENCE_PROMPT,
    USER_SUBMISSION_ANALYSIS_PROMPT,
)
from codememory.ai.providers.base_provider import (
    BaseAIProvider,
    InterpretationResult,
    serialize_evidence,
)
from codememory.ai.providers.heuristic_provider import HeuristicAIProvider
from codememory.domain.models import Problem, Submission

logger = logging.getLogger(__name__)


def extract_json_payload(text: str) -> str:
    """Extract clean JSON string from model response text, removing markdown fences if present."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove opening ```json or ```
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        # Remove closing ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


class Qwen3Provider(BaseAIProvider):
    """Qwen3 local AI provider for grounded insight interpretation and DSA code analysis.

    Communicates with a local OpenAI-compatible endpoint (e.g., llama.cpp server,
    Ollama, LM Studio, vLLM) hosting a quantized Qwen3 model.
    Falls back gracefully to HeuristicAIProvider on any connection, timeout, parsing,
    or schema validation failure.
    """

    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout_seconds: float = 30.0,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        custom_client: Optional[Any] = None,
    ):
        self.endpoint_url = (
            endpoint_url
            or os.environ.get("QWEN_ENDPOINT_URL")
            or os.environ.get("QWEN_BASE_URL")
            or "http://localhost:11434/v1"
        )
        self.model_name = (
            model_name
            or os.environ.get("QWEN_MODEL_NAME")
            or os.environ.get("QWEN_MODEL_PATH")
            or "qwen3:8b"
        )
        self.api_key = api_key or os.environ.get("QWEN_API_KEY", "qwen")
        self.timeout_seconds = float(os.environ.get("QWEN_TIMEOUT_SECONDS", str(timeout_seconds)))
        self.temperature = float(os.environ.get("QWEN_TEMPERATURE", str(temperature)))
        self.max_tokens = int(os.environ.get("QWEN_MAX_TOKENS", str(max_tokens)))
        self.ai_enabled = os.environ.get("AI_ENABLED", "true").lower() in ("true", "1", "yes")
        self.fallback = HeuristicAIProvider()
        self._custom_client = custom_client  # Injectable fake client for unit tests / offline CI

    def is_available(self) -> bool:
        """Check if AI provider is enabled."""
        return self.ai_enabled

    def _call_model(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format_json: bool = True,
    ) -> str:
        """Invoke local Qwen3 runtime or custom client, returning raw completion text."""
        if not self.is_available():
            raise RuntimeError("Qwen3Provider is disabled via AI_ENABLED=false")

        # Use custom client adapter if injected (e.g. for unit testing without network/server)
        if self._custom_client is not None:
            if callable(self._custom_client):
                return self._custom_client(system_prompt, user_prompt)
            elif hasattr(self._custom_client, "chat_completion"):
                return self._custom_client.chat_completion(system_prompt, user_prompt)

        # Try using `openai` SDK client pointing to local base_url
        try:
            # pyrefly: ignore [missing-import]
            import openai
            client = openai.OpenAI(
                base_url=self.endpoint_url,
                api_key=self.api_key,
                timeout=self.timeout_seconds,
            )
            kwargs: dict[str, Any] = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            }
            if response_format_json:
                kwargs["response_format"] = {"type": "json_object"}
            
            response = client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""
        except ImportError:
            pass  # Fall back to standard library HTTP request below

        # HTTP fallback using standard library urllib if openai SDK is not available or fails setup
        chat_url = f"{self.endpoint_url.rstrip('/')}/chat/completions"
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if response_format_json:
            payload["response_format"] = {"type": "json_object"}

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            chat_url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body["choices"][0]["message"]["content"] or ""

    def analyze_submission(
        self,
        submission: Submission,
        problem: Problem,
        previous_submission: Optional[Submission] = None,
    ) -> SubmissionAnalysis:
        """Analyze a submission attempt using local Qwen3 model with heuristic fallback."""
        if not self.is_available():
            return self.fallback.analyze_submission(submission, problem, previous_submission)

        try:
            prev_ctx = "None"
            if previous_submission:
                prev_ctx = f"Status: {previous_submission.status.value}, Code: {previous_submission.code[:200]}..."

            prompt = USER_SUBMISSION_ANALYSIS_PROMPT.format(
                problem_title=problem.title,
                difficulty=problem.difficulty.value if hasattr(problem.difficulty, "value") else str(problem.difficulty),
                topics=", ".join(problem.topics) if problem.topics else "None",
                statement=problem.statement or "Not provided",
                status=submission.status.value if hasattr(submission.status, "value") else str(submission.status),
                language=submission.language,
                runtime_ms=f"{submission.runtime_ms:.1f}" if submission.runtime_ms is not None else "N/A",
                memory_mb=f"{submission.memory_mb:.1f}" if submission.memory_mb is not None else "N/A",
                error_message=submission.error_message or "None",
                code=submission.code or "",
                previous_context=prev_ctx,
            )

            raw_text = self._call_model(SYSTEM_SUBMISSION_ANALYSIS_PROMPT, prompt, response_format_json=True)
            clean_json = extract_json_payload(raw_text)
            raw_data = json.loads(clean_json)
            return SubmissionAnalysis.model_validate(raw_data)

        except Exception as e:
            logger.warning("Qwen3Provider analyze_submission failed (%s). Falling back to heuristic provider.", e)
            return self.fallback.analyze_submission(submission, problem, previous_submission)

    def analyze_evolution(
        self,
        problem: Problem,
        submissions: List[Submission],
    ) -> SolutionEvolution:
        """Analyze solution evolution across attempts using local Qwen3 model with heuristic fallback."""
        if not self.is_available() or not submissions:
            return self.fallback.analyze_evolution(problem, submissions)

        try:
            sorted_subs = sorted(submissions, key=lambda s: s.submitted_at)
            attempts_formatted = "\n".join(
                f"Attempt {idx} ({s.status.value}): Code length {len(s.code or '')} chars, Runtime {s.runtime_ms or 'N/A'} ms\n```\n{s.code[:300]}\n```"
                for idx, s in enumerate(sorted_subs, start=1)
            )

            prompt = USER_EVOLUTION_ANALYSIS_PROMPT.format(
                problem_id=problem.id,
                problem_title=problem.title,
                total_attempts=len(sorted_subs),
                attempts_formatted=attempts_formatted,
            )

            raw_text = self._call_model(SYSTEM_EVOLUTION_ANALYSIS_PROMPT, prompt, response_format_json=True)
            clean_json = extract_json_payload(raw_text)
            raw_data = json.loads(clean_json)

            evolution = SolutionEvolution.model_validate(raw_data)
            if not evolution.steps:
                fallback_evo = self.fallback.analyze_evolution(problem, submissions)
                evolution.steps = fallback_evo.steps
            return evolution

        except Exception as e:
            logger.warning("Qwen3Provider analyze_evolution failed (%s). Falling back to heuristic provider.", e)
            return self.fallback.analyze_evolution(problem, submissions)

    def answer_question(self, question: str, context: str) -> str:
        """Answer grounded query using local Qwen3 model with heuristic fallback."""
        if not self.is_available():
            return self.fallback.answer_question(question, context)

        try:
            prompt = USER_ASK_CODEMEMORY_PROMPT.format(question=question, context=context)
            raw_text = self._call_model(SYSTEM_ASK_CODEMEMORY_PROMPT, prompt, response_format_json=False)
            return raw_text.strip() or "No response generated."
        except Exception as e:
            logger.warning("Qwen3Provider answer_question failed (%s). Falling back to heuristic provider.", e)
            return self.fallback.answer_question(question, context)

    def interpret_evidence(self, evidence: InsightEvidence) -> InterpretationResult:
        """Interpret structured evidence using local Qwen3 provider into Grounded Insight output shape.

        Enforces grounding rules:
        - Parses structured JSON strictly.
        - Validates evidence_refs against evidence.all_evidence_ids().
        - Strips any unknown evidence IDs generated by model.
        - Falls back safely to HeuristicAIProvider on model error, network error, timeout,
          invalid JSON, or validation failure.
        """
        if not self.is_available():
            return self.fallback.interpret_evidence(evidence)

        try:
            evidence_text = serialize_evidence(evidence)
            prompt = USER_INTERPRET_EVIDENCE_PROMPT.format(evidence_text=evidence_text)

            raw_text = self._call_model(SYSTEM_INTERPRET_EVIDENCE_PROMPT, prompt, response_format_json=True)
            clean_json = extract_json_payload(raw_text)
            raw_data = json.loads(clean_json)
            result = InterpretationResult.model_validate(raw_data)

            # Strict evidence ref validation: strip any evidence IDs that do not exist in source evidence
            valid_ids = evidence.all_evidence_ids()
            result.evidence_refs = [ref for ref in result.evidence_refs if ref in valid_ids]

            return result

        except Exception as e:
            logger.warning("Qwen3Provider interpret_evidence failed (%s). Falling back to heuristic provider.", e)
            return self.fallback.interpret_evidence(evidence)
