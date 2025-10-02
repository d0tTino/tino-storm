import pytest

import importlib

import tino_storm.search as search_module
from tino_storm.providers import ProviderAggregator


def _clear_provider_cache():
    global search_module
    search_module = importlib.import_module("tino_storm.search")
    from tino_storm.providers.docs_hub import DocsHubProvider
    from tino_storm.providers.parallel import ParallelProvider
    registry = search_module.provider_registry
    if "docs_hub" not in registry.available():
        registry.register("docs_hub", DocsHubProvider)
    if "parallel" not in registry.available():
        registry.register("parallel", ParallelProvider)
    with search_module._PROVIDER_CACHE_LOCK:
        search_module._PROVIDER_CACHE.clear()


def test_default_provider_is_cached(monkeypatch):
    monkeypatch.delenv("STORM_SEARCH_PROVIDER", raising=False)
    _clear_provider_cache()

    first = search_module._resolve_provider(None)
    second = search_module._resolve_provider(None)

    assert first is second


@pytest.mark.parametrize(
    "env_value",
    [
        "docs_hub,parallel",
        "docs_hub, parallel",
    ],
)
def test_env_provider_list_builds_aggregator(monkeypatch, env_value):
    _clear_provider_cache()
    monkeypatch.setenv("STORM_SEARCH_PROVIDER", env_value)

    provider = search_module._resolve_provider(None)

    assert isinstance(provider, ProviderAggregator)
    assert len(provider.providers) == 2
    assert search_module._resolve_provider(None) is provider

    monkeypatch.delenv("STORM_SEARCH_PROVIDER")

