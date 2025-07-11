"""Registry helper for retriever providers."""

from __future__ import annotations

from typing import Type

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - only for type checking
    from knowledge_storm import rm as _rm  # noqa: F401

RETRIEVER_REGISTRY: dict[str, str] = {
    "you": "YouRM",
    "bing": "BingSearch",
    "brave": "BraveRM",
    "serper": "SerperRM",
    "duckduckgo": "DuckDuckGoSearchRM",
    "tavily": "TavilySearchRM",
    "vector": "VectorRM",
    "searxng": "SearXNG",
    "azure_ai_search": "AzureAISearch",
    "arxiv": "StanfordOvalArxivRM",
    "rrf": "RRFRetriever",
}


def get_retriever(name: str) -> Type:
    """Return the retriever class mapped to ``name``."""
    key = name.lower()
    if key not in RETRIEVER_REGISTRY:
        raise ValueError(f"Unknown retriever provider: {name}")
    if key == "rrf":
        from tino_storm.rrf import RRFRetriever

        return RRFRetriever
    module = importlib.import_module("knowledge_storm.rm")
    return getattr(module, RETRIEVER_REGISTRY[key])
