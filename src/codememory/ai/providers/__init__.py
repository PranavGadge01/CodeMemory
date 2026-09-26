"""AI Provider exports and factory."""

import os
from typing import Optional

from codememory.ai.providers.base_provider import BaseAIProvider
from codememory.ai.providers.heuristic_provider import HeuristicAIProvider
from codememory.ai.providers.openai_provider import OpenAIProvider
from codememory.ai.providers.qwen_provider import Qwen3Provider


def get_ai_provider(provider_name: Optional[str] = None, **kwargs) -> BaseAIProvider:
    """Factory to instantiate AI provider based on name or AI_PROVIDER environment variable.

    Supported provider names:
    - 'qwen': Qwen3 local model provider
    - 'openai': OpenAI cloud model provider
    - 'heuristic': Offline rule-based heuristic provider (default fallback)
    """
    name = (provider_name or os.environ.get("AI_PROVIDER") or "").lower()
    if name == "qwen":
        return Qwen3Provider(**kwargs)
    elif name == "openai":
        return OpenAIProvider(**kwargs)
    elif name == "heuristic":
        return HeuristicAIProvider()

    # Fallback auto-detection: if OPENAI_API_KEY is present, default to OpenAIProvider
    if os.environ.get("OPENAI_API_KEY"):
        return OpenAIProvider(**kwargs)

    return HeuristicAIProvider()


__all__ = [
    "BaseAIProvider",
    "HeuristicAIProvider",
    "OpenAIProvider",
    "Qwen3Provider",
    "get_ai_provider",
]
