"""Registry helper for retriever providers."""

from __future__ import annotations

from typing import Type

from knowledge_storm.rm import (
    YouRM,
    BingSearch,
    BraveRM,
    SerperRM,
    DuckDuckGoSearchRM,
    TavilySearchRM,
    VectorRM,
    SearXNG,
    AzureAISearch,
    StanfordOvalArxivRM,
)

RETRIEVER_REGISTRY: dict[str, Type] = {
    "you": YouRM,
    "bing": BingSearch,
    "brave": BraveRM,
    "serper": SerperRM,
    "duckduckgo": DuckDuckGoSearchRM,
    "tavily": TavilySearchRM,
    "vector": VectorRM,
    "searxng": SearXNG,
    "azure_ai_search": AzureAISearch,
    "arxiv": StanfordOvalArxivRM,
}


def get_retriever(name: str) -> Type:
    """Return the retriever class mapped to ``name``."""
    key = name.lower()
    if key not in RETRIEVER_REGISTRY:
        raise ValueError(f"Unknown retriever provider: {name}")
    return RETRIEVER_REGISTRY[key]
