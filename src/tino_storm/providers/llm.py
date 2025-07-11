"""Registry helper for language model providers."""

from __future__ import annotations

from typing import Type

import importlib
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


def get_llm(name: str) -> Type:
    """Return the language model class mapped to ``name``."""
    key = name.lower()
    if key not in LLM_REGISTRY:
        raise ValueError(f"Unknown LLM provider: {name}")
    module = importlib.import_module("knowledge_storm.lm")
    return getattr(module, LLM_REGISTRY[key])
