import asyncio

from typing import List

from tino_storm.providers.base import Provider
from tino_storm.providers.registry import provider_registry
from tino_storm.providers.aggregator import ProviderAggregator, canonical_url
from tino_storm.search import _resolve_provider, search_async, search_sync
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


class RankingProvider(Provider):
    def __init__(self, name: str, payload):
        self.name = name
        self._payload = payload

    def _build(self):
        return [
            ResearchResult(
                url=item["url"],
                snippets=item.get("snippets", []),
                meta=item.get("meta", {}),
                summary=item.get("summary"),
                score=item.get("score"),
                posterior=item.get("posterior"),
            )
            for item in self._payload
        ]

    async def search_async(self, query, vaults, **kwargs):
        return self._build()

    def search_sync(self, query, vaults, **kwargs):
        return self._build()


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


def test_search_sync_dedupes_and_emits_event(monkeypatch):
    # Reset event subscribers and capture emitted events
    monkeypatch.setattr(event_emitter, "_subscribers", {})
    events = []

    def handler(event: ResearchAdded) -> None:
        events.append(event)

    event_emitter.subscribe(ResearchAdded, handler)

    provider = ProviderAggregator([DuplicateProvider(), FailingProvider()])

    results = provider.search_sync("q", [])
    assert {r.url for r in results} == {"dup"}
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
    sync_results = search_sync("q", [], provider="slow,fast", timeout=0.01)
    assert {r.url for r in sync_results} == {"fast"}
    assert len(events) == 1
    assert events[0].topic == "slow"
    assert events[0].information_table["error"] == "timeout"


def test_search_sync_inside_running_event_loop():
    provider = ProviderAggregator([DummyProvider("p")])

    async def run():
        # Invoking search_sync while an event loop is already running should work
        return provider.search_sync("q", [])

    results = asyncio.run(run())
    assert {r.url for r in results} == {"p"}


def test_aggregator_throttles_max_concurrency():
    current = 0
    peak = 0

    class CountingProvider(Provider):
        def __init__(self, name: str):
            self.name = name

        async def search_async(self, query, vaults, **kwargs):
            nonlocal current, peak
            current += 1
            peak = max(peak, current)
            await asyncio.sleep(0.01)
            current -= 1
            return [ResearchResult(url=self.name, snippets=[], meta={})]

        def search_sync(self, query, vaults, **kwargs):  # pragma: no cover - not used
            return [ResearchResult(url=self.name, snippets=[], meta={})]

    providers = [CountingProvider("p1"), CountingProvider("p2"), CountingProvider("p3")]
    aggregator = ProviderAggregator(providers, max_concurrency=1)

    async def run():
        return await aggregator.search_async("q", [])

    results = asyncio.run(run())
    assert {r.url for r in results} == {"p1", "p2", "p3"}
    assert peak == 1


def test_rrf_fusion_preserves_metadata_and_trims():
    provider_a = RankingProvider(
        "a",
        [
            {
                "url": "https://example.com/a",
                "summary": "Alpha",
                "score": 0.2,
                "posterior": 0.1,
            },
            {
                "url": "https://example.com/b",
                "summary": "Short",
                "score": 0.7,
                "meta": {"source": "a"},
            },
            {
                "url": "https://example.com/c",
                "summary": "Gamma",
                "score": 0.1,
            },
        ],
    )
    provider_b = RankingProvider(
        "b",
        [
            {
                "url": "https://example.com/b?ref=1",
                "summary": "Longer summary for B",
                "score": 0.95,
                "posterior": 0.8,
                "meta": {"source": "b"},
            },
            {
                "url": "https://example.com/d",
                "summary": "Delta",
                "score": 0.5,
            },
            {
                "url": "https://example.com/a",
                "summary": "Alpha extended",
                "score": 0.4,
            },
        ],
    )

    aggregator = ProviderAggregator([provider_a, provider_b])

    async_results = asyncio.run(
        aggregator.search_async("q", [], k_per_vault=3, rrf_k=2)
    )
    assert [canonical_url(r.url) for r in async_results] == [
        "https://example.com/b",
        "https://example.com/a",
    ]
    assert len(async_results) == 2

    top = async_results[0]
    assert top.summary == "Longer summary for B"
    assert top.score == 0.95
    assert top.posterior == 0.8
    assert top.meta["source"] == "b"

    sync_results = aggregator.search_sync("q", [], k_per_vault=3, rrf_k=2)
    assert [canonical_url(r.url) for r in sync_results] == [
        "https://example.com/b",
        "https://example.com/a",
    ]
    assert len(sync_results) == 2
