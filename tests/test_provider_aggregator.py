import asyncio

from typing import List

from tino_storm.providers.base import Provider
from tino_storm.providers.registry import provider_registry
from tino_storm.providers.aggregator import ProviderAggregator, canonical_url
from tino_storm.search import _resolve_provider, search, search_async
from tino_storm.search_result import ResearchResult
from tino_storm.events import ResearchAdded, event_emitter


class DummyProvider(Provider):
    def __init__(self, name: str):
        self.name = name

    async def search_async(self, query, vaults, **kwargs):
        return [ResearchResult(url=self.name, snippets=[], meta={})]

    def search_sync(self, query, vaults, **kwargs):
        return [ResearchResult(url=self.name, snippets=[], meta={})]


class FailingProvider(Provider):
    name = "failing"

    async def search_async(self, query, vaults, **kwargs):
        raise RuntimeError("boom")

    def search_sync(self, query, vaults, **kwargs):
        raise RuntimeError("boom")


class DuplicateProvider(Provider):
    name = "dup"

    async def search_async(self, query, vaults, **kwargs):
        return [
            ResearchResult(url="dup", snippets=[], meta={}),
            ResearchResult(url="dup", snippets=[], meta={}),
        ]

    def search_sync(self, query, vaults, **kwargs):
        return [
            ResearchResult(url="dup", snippets=[], meta={}),
            ResearchResult(url="dup", snippets=[], meta={}),
        ]


class QueryVariantProviderA(Provider):
    name = "qa"

    async def search_async(self, query, vaults, **kwargs):
        return [
            ResearchResult(url="https://example.com/path?a=1&b=2", snippets=[], meta={})
        ]

    def search_sync(self, query, vaults, **kwargs):
        return [
            ResearchResult(url="https://example.com/path?a=1&b=2", snippets=[], meta={})
        ]


class QueryVariantProviderB(Provider):
    name = "qb"

    async def search_async(self, query, vaults, **kwargs):
        return [
            ResearchResult(url="https://example.com/path?b=2&a=1", snippets=[], meta={})
        ]

    def search_sync(self, query, vaults, **kwargs):
        return [
            ResearchResult(url="https://example.com/path?b=2&a=1", snippets=[], meta={})
        ]


class SlowProvider(Provider):
    name = "slow"

    async def search_async(self, query, vaults, **kwargs):
        await asyncio.sleep(0.05)
        return [ResearchResult(url="slow", snippets=[], meta={})]

    def search_sync(self, query, vaults, **kwargs):
        import time

        time.sleep(0.05)
        return [ResearchResult(url="slow", snippets=[], meta={})]


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

    sync_results = provider.search_sync("q", [])
    assert {r.url for r in sync_results} == {"p1", "p2"}


def test_aggregator_skips_failures(monkeypatch):
    monkeypatch.setattr(provider_registry, "_providers", {})
    provider_registry.register("good", DummyProvider("good"))
    provider_registry.register("bad", FailingProvider())

    provider = _resolve_provider("good,bad")

    async def run_async():
        return await provider.search_async("q", [])

    async_results = asyncio.run(run_async())
    assert {r.url for r in async_results} == {"good"}

    sync_results = provider.search_sync("q", [])
    assert {r.url for r in sync_results} == {"good"}


def test_aggregator_emits_event_and_deduplicates(monkeypatch):
    monkeypatch.setattr(provider_registry, "_providers", {})
    provider_registry.register("dup", DuplicateProvider())
    provider_registry.register("bad", FailingProvider())

    # Reset event subscribers and capture emitted events
    monkeypatch.setattr(event_emitter, "_subscribers", {})
    events = []

    def handler(event: ResearchAdded) -> None:
        events.append(event)

    event_emitter.subscribe(ResearchAdded, handler)

    provider = _resolve_provider("dup,bad")

    async def run_async():
        return await provider.search_async("q", [])

    async_results = asyncio.run(run_async())
    assert {r.url for r in async_results} == {"dup"}
    assert len(events) == 1
    assert events[0].topic == "failing"
    assert events[0].information_table["error"] == "boom"

    events.clear()
    sync_results = provider.search_sync("q", [])
    assert {r.url for r in sync_results} == {"dup"}
    assert len(events) == 1
    assert events[0].topic == "failing"
    assert events[0].information_table["error"] == "boom"


def test_aggregator_returns_research_results():
    provider = ProviderAggregator([DummyProvider("p")])
    async_results = asyncio.run(provider.search_async("q", []))
    assert all(isinstance(r, ResearchResult) for r in async_results)
    sync_results = provider.search_sync("q", [])
    assert all(isinstance(r, ResearchResult) for r in sync_results)


def test_query_string_variants_are_deduplicated():
    provider = ProviderAggregator([QueryVariantProviderA(), QueryVariantProviderB()])

    async_results = asyncio.run(provider.search_async("q", []))
    assert len(async_results) == 1
    assert canonical_url(async_results[0].url) == "https://example.com/path"

    sync_results = provider.search_sync("q", [])
    assert len(sync_results) == 1
    assert canonical_url(sync_results[0].url) == "https://example.com/path"


def test_timeout_emits_event_and_skips_provider(monkeypatch):
    monkeypatch.setattr(provider_registry, "_providers", {})
    provider_registry.register("slow", SlowProvider())
    provider_registry.register("fast", DummyProvider("fast"))

    # Reset subscribers and capture events
    monkeypatch.setattr(event_emitter, "_subscribers", {})
    events: List[ResearchAdded] = []

    def handler(event: ResearchAdded) -> None:
        events.append(event)

    event_emitter.subscribe(ResearchAdded, handler)

    orig_wait_for = asyncio.wait_for

    async def wait_for_wrapper(*args, **kwargs):
        try:
            return await orig_wait_for(*args, **kwargs)
        except asyncio.TimeoutError:
            raise asyncio.TimeoutError("timeout")

    monkeypatch.setattr(asyncio, "wait_for", wait_for_wrapper)

    async def run_async():
        return await search_async("q", [], provider="slow,fast", timeout=0.01)

    async_results = asyncio.run(run_async())
    assert {r.url for r in async_results} == {"fast"}
    assert len(events) == 1
    assert events[0].topic == "slow"
    assert events[0].information_table["error"] == "timeout"

    events.clear()
    sync_results = search("q", [], provider="slow,fast", timeout=0.01)
    assert {r.url for r in sync_results} == {"fast"}
    assert len(events) == 1
    assert events[0].topic == "slow"
    assert events[0].information_table["error"] == "timeout"
