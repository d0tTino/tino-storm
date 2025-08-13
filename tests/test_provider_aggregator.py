import asyncio

from tino_storm.providers.base import Provider
from tino_storm.providers.registry import provider_registry
from tino_storm.providers.aggregator import ProviderAggregator
from tino_storm.search import _resolve_provider


class DummyProvider(Provider):
    def __init__(self, name: str):
        self.name = name

    async def search_async(self, query, vaults, **kwargs):
        return [{"url": self.name, "snippets": [], "meta": {}}]

    def search_sync(self, query, vaults, **kwargs):
        return [{"url": self.name, "snippets": [], "meta": {}}]


class FailingProvider(Provider):
    name = "failing"

    async def search_async(self, query, vaults, **kwargs):
        raise RuntimeError("boom")

    def search_sync(self, query, vaults, **kwargs):
        raise RuntimeError("boom")


def test_resolve_provider_aggregates_and_runs_concurrently(monkeypatch):
    monkeypatch.setattr(provider_registry, "_providers", {})
    provider_registry.register("p1", DummyProvider("p1"))
    provider_registry.register("p2", DummyProvider("p2"))

    gathered = {}
    orig_gather = asyncio.gather

    async def gather_wrapper(*tasks, **kwargs):
        gathered["count"] = len(tasks)
        return await orig_gather(*tasks, **kwargs)

    monkeypatch.setattr(asyncio, "gather", gather_wrapper)

    provider = _resolve_provider("p1,p2")
    assert isinstance(provider, ProviderAggregator)

    async def run():
        return await provider.search_async("q", [])

    results = asyncio.run(run())

    assert gathered["count"] == 2
    assert {r["url"] for r in results} == {"p1", "p2"}

    sync_results = provider.search_sync("q", [])
    assert {r["url"] for r in sync_results} == {"p1", "p2"}


def test_aggregator_skips_failures(monkeypatch):
    monkeypatch.setattr(provider_registry, "_providers", {})
    provider_registry.register("good", DummyProvider("good"))
    provider_registry.register("bad", FailingProvider())

    provider = _resolve_provider("good,bad")

    async def run_async():
        return await provider.search_async("q", [])

    async_results = asyncio.run(run_async())
    assert {r["url"] for r in async_results} == {"good"}

    sync_results = provider.search_sync("q", [])
    assert {r["url"] for r in sync_results} == {"good"}
