"""Registry helper for language model providers."""

from __future__ import annotations

from typing import Type

import importlib
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - only for type checking
    from knowledge_storm import lm as _lm  # noqa: F401

LLM_REGISTRY: dict[str, str] = {
    "litellm": "LitellmModel",
    "openai": "OpenAIModel",
    "azure": "AzureOpenAIModel",
    "deepseek": "DeepSeekModel",
    "groq": "GroqModel",
    "claude": "ClaudeModel",
    "vllm": "VLLMClient",
    "ollama": "OllamaClient",
    "tgi": "TGIClient",
    "together": "TogetherClient",
    "gemini": "GoogleModel",
    "google": "GoogleModel",
}

CLOUD_LLMS = {
    "openai",
    "azure",
    "deepseek",
    "groq",
    "claude",
    "together",
    "gemini",
    "google",
}


def get_llm(name: str, cloud_allowed: bool | None = None) -> Type:
    """Return the language model class mapped to ``name`` respecting ``cloud_allowed``."""
    if cloud_allowed is None:
        cloud_allowed = os.getenv("STORM_CLOUD_ALLOWED", "true").lower() != "false"

    key = name.lower()
    if key not in LLM_REGISTRY:
        raise ValueError(f"Unknown LLM provider: {name}")
    if not cloud_allowed and key in CLOUD_LLMS:
        raise ValueError(f"Cloud LLM provider '{name}' is disabled")
    module = importlib.import_module("knowledge_storm.lm")
    return getattr(module, LLM_REGISTRY[key])
