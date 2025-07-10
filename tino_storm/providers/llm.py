"""Registry helper for language model providers."""

from __future__ import annotations

from typing import Type

from knowledge_storm.lm import (
    LitellmModel,
    OpenAIModel,
    AzureOpenAIModel,
    DeepSeekModel,
    GroqModel,
    ClaudeModel,
    VLLMClient,
    OllamaClient,
    TGIClient,
    TogetherClient,
    GoogleModel,
)

LLM_REGISTRY: dict[str, Type] = {
    "litellm": LitellmModel,
    "openai": OpenAIModel,
    "azure": AzureOpenAIModel,
    "deepseek": DeepSeekModel,
    "groq": GroqModel,
    "claude": ClaudeModel,
    "vllm": VLLMClient,
    "ollama": OllamaClient,
    "tgi": TGIClient,
    "together": TogetherClient,
    "gemini": GoogleModel,
    "google": GoogleModel,
}


def get_llm(name: str) -> Type:
    """Return the language model class mapped to ``name``."""
    key = name.lower()
    if key not in LLM_REGISTRY:
        raise ValueError(f"Unknown LLM provider: {name}")
    return LLM_REGISTRY[key]
