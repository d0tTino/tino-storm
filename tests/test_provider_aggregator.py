import asyncio

from tino_storm import search as search_fn
from tino_storm.providers import Provider, provider_registry, ProviderAggregator
from tino_storm.search_result import ResearchResult
from tino_storm.search import _resolve_provider


class DummyProvider(Provider):
    def __init__(self, name: str):
        self.name = name

    async def search_async(self, query, vaults, **kwargs):
        return [ResearchResult(url=self.name, snippets=[], meta={})]

    def search_sync(self, query, vaults, **kwargs):
        return [ResearchResult(url=self.name, snippets=[], meta={})]


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
    assert {r.url for r in results} == {"p1", "p2"}

    sync_results = search_fn("q", [], provider="p1,p2")
    assert {r.url for r in sync_results} == {"p1", "p2"}
