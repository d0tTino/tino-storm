from __future__ import annotations

import os
from dataclasses import dataclass
from importlib import import_module
from typing import Dict, Optional, TYPE_CHECKING

from .base import Provider, DefaultProvider, load_provider
from .registry import ProviderRegistry, provider_registry, register_provider

if TYPE_CHECKING:  # pragma: no cover
    from .aggregator import ProviderAggregator
    from .docs_hub import DocsHubProvider
    from .multi_source import MultiSourceProvider
    from .parallel import ParallelProvider
    from .vector_db import VectorDBProvider

_LAZY_ATTRS = {
    "ParallelProvider": ("tino_storm.providers.parallel", "ParallelProvider"),
    "ProviderAggregator": ("tino_storm.providers.aggregator", "ProviderAggregator"),
    "DocsHubProvider": ("tino_storm.providers.docs_hub", "DocsHubProvider"),
    "MultiSourceProvider": ("tino_storm.providers.multi_source", "MultiSourceProvider"),
    "VectorDBProvider": ("tino_storm.providers.vector_db", "VectorDBProvider"),
}

_LAZY_SUBMODULES = {
    "aggregator",
    "base",
    "docs_hub",
    "multi_source",
    "parallel",
    "registry",
    "vector_db",
}


@dataclass(frozen=True)
class ProviderCapabilities:
    """Describe which optional search providers are usable."""

    docs_hub: bool
    docs_hub_remote: bool
    vector_retriever: bool
    bing: bool


def __getattr__(name: str):
    if name in _LAZY_ATTRS:
        module_name, attr = _LAZY_ATTRS[name]
        module = import_module(module_name)
        value = getattr(module, attr)
        globals()[name] = value
        return value
    if name in _LAZY_SUBMODULES:
        module = import_module(f"{__name__}.{name}")
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def provider_capabilities() -> ProviderCapabilities:
    """Return lightweight availability flags for optional providers."""

    docs_hub_provider = provider_registry.available().get("docs_hub")
    has_docs_hub = docs_hub_provider is not None
    docs_hub_remote = bool(
        docs_hub_provider
        and getattr(docs_hub_provider, "is_remote_configured", False)
    )

    vector_provider = provider_registry.available().get("vector_db")
    has_vector_retriever = bool(
        vector_provider and getattr(vector_provider, "retriever", None)
    )

    has_bing = bool(os.getenv("BING_SEARCH_API_KEY"))

    return ProviderCapabilities(
        docs_hub=has_docs_hub,
        docs_hub_remote=docs_hub_remote,
        vector_retriever=has_vector_retriever,
        bing=has_bing,
    )


def available_providers() -> Dict[str, bool]:
    """Advertise optional providers in a dictionary friendly for UIs."""

    capabilities = provider_capabilities()
    return {
        "default": True,
        "bing": capabilities.bing,
        "docs_hub": capabilities.docs_hub,
        "docs_hub_remote": capabilities.docs_hub_remote,
        "vector_db": capabilities.vector_retriever,
    }


def get_docs_hub_provider() -> Optional[Provider]:
    """Return the Docs Hub provider when a remote endpoint is configured."""

    provider = provider_registry.available().get("docs_hub")
    if provider and getattr(provider, "is_remote_configured", False):
        return provider
    return None


def get_vector_db_provider() -> Optional[Provider]:
    """Return the vector search provider when a retriever is attached."""

    provider = provider_registry.available().get("vector_db")
    if provider and getattr(provider, "retriever", None):
        return provider
    return None


__all__ = [
    "Provider",
    "DefaultProvider",
    "ParallelProvider",
    "ProviderAggregator",
    "DocsHubProvider",
    "MultiSourceProvider",
    "VectorDBProvider",
    "load_provider",
    "ProviderRegistry",
    "provider_registry",
    "register_provider",
    "ProviderCapabilities",
    "provider_capabilities",
    "available_providers",
    "get_docs_hub_provider",
    "get_vector_db_provider",
]
