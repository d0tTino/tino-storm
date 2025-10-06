import asyncio
import sys
import threading
import types
from concurrent.futures import ThreadPoolExecutor

import pytest
from tino_storm.providers import (
    Provider,
    load_provider,
    ParallelProvider,
    DefaultProvider,
)
from tino_storm.search import (
    _resolve_provider,
    search_sync as search_fn,
    _PROVIDER_CACHE,
    ResearchError,
)
from tino_storm.events import ResearchAdded, event_emitter
from tino_storm.search_result import ResearchResult


def test_load_provider_raises(monkeypatch):
    mod = types.ModuleType("dummy_mod")

    class NotProvider:
        pass

    mod.NotProvider = NotProvider
    monkeypatch.setitem(sys.modules, "dummy_mod", mod)

    with pytest.raises(TypeError):
        load_provider("dummy_mod.NotProvider")


def test_resolve_provider_invalid_string(monkeypatch):
    mod = types.ModuleType("dummy_mod2")

    class NotProvider:
        pass

    mod.NotProvider = NotProvider
    monkeypatch.setitem(sys.modules, "dummy_mod2", mod)

    monkeypatch.setattr(event_emitter, "_subscribers", {})
    events = []

    async def handler(e):
        events.append(e)

    event_emitter.subscribe(ResearchAdded, handler)

    with pytest.raises(ResearchError) as exc:
        _resolve_provider("dummy_mod2.NotProvider")

    assert len(events) == 1
    assert events[0].topic == "dummy_mod2.NotProvider"
    assert "error" in events[0].information_table
    assert exc.value.provider_spec == "dummy_mod2.NotProvider"


def test_resolve_provider_emits_event_on_failure():
    events: list[ResearchAdded] = []

    def handler(event: ResearchAdded) -> None:
        events.append(event)

    event_emitter.subscribe(ResearchAdded, handler)
    with pytest.raises(ResearchError) as exc:
        _resolve_provider("nonexistent.module.Provider")
    event_emitter.unsubscribe(ResearchAdded, handler)

    assert len(events) == 1
    event = events[0]
    assert event.topic == "nonexistent.module.Provider"
    assert "No module named" in event.information_table["error"]
    assert exc.value.provider_spec == "nonexistent.module.Provider"


def test_search_uses_env_provider(monkeypatch):
    calls = {}

    class DummyProvider(Provider):
        def search_sync(
            self,
            query,
            vaults,
            *,
            k_per_vault=5,
            rrf_k=60,
            chroma_path=None,
            vault=None,
            timeout=None,
        ):
            calls["args"] = (
                query,
                list(vaults),
                k_per_vault,
                rrf_k,
                chroma_path,
                vault,
                timeout,
            )
            return [ResearchResult(url="ok", snippets=[], meta={})]

    mod = types.ModuleType("dummy_provider_mod")
    mod.DummyProvider = DummyProvider
    monkeypatch.setitem(sys.modules, "dummy_provider_mod", mod)
    monkeypatch.setenv("STORM_SEARCH_PROVIDER", "dummy_provider_mod.DummyProvider")

    result = search_fn("q", ["v"])

    assert result == [ResearchResult(url="ok", snippets=[], meta={})]
    assert calls["args"] == ("q", ["v"], 5, 60, None, None, None)


def test_parallel_provider_gathers_and_merges(monkeypatch):
    gathered = {}

    orig_gather = asyncio.gather

    async def gather_wrapper(*tasks, **kwargs):
        gathered["count"] = len(tasks)
        return await orig_gather(*tasks, **kwargs)

    async def fake_to_thread(func, *a, **k):
        return func(*a, **k)

    monkeypatch.setattr(asyncio, "gather", gather_wrapper)
    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(
        "tino_storm.providers.parallel.search_vaults",
        lambda *a, **k: [{"url": "vault", "snippets": [], "meta": {}}],
    )
    provider = ParallelProvider()
    monkeypatch.setattr(
        provider,
        "_bing_search",
        lambda *args, **kwargs: [
            {"url": "bing", "description": "desc", "title": "t"}
        ],
    )

    async def run():
        return await provider.search_async("q", ["v"])

    results = asyncio.run(run())

    assert gathered["count"] == 2
    assert {r.url for r in results} == {"vault", "bing"}
    bing_result = next(r for r in results if r.url == "bing")
    assert bing_result.snippets == ["desc"]
    assert bing_result.meta["title"] == "t"


def test_default_provider_formats_bing(monkeypatch):
    monkeypatch.setattr("tino_storm.providers.base.search_vaults", lambda *a, **k: [])
    provider = DefaultProvider()
    monkeypatch.setattr(
        provider,
        "_bing_search",
        lambda *args, **kwargs: [
            {"url": "u", "description": "d", "title": "t"}
        ],
    )
    results = provider.search_sync("q", [])
    assert results == [
        ResearchResult(url="u", snippets=["d"], meta={"title": "t"}, summary="d")
    ]


def test_resolve_provider_caches_instance(monkeypatch):
    calls = {"count": 0}

    class DummyProvider(Provider):
        def __init__(self):
            calls["count"] += 1

        def search_sync(self, *a, **k):
            return []

    mod = types.ModuleType("dummy_provider_cache_mod")
    mod.DummyProvider = DummyProvider
    monkeypatch.setitem(sys.modules, "dummy_provider_cache_mod", mod)

    _PROVIDER_CACHE.clear()
    try:
        provider1 = _resolve_provider("dummy_provider_cache_mod.DummyProvider")
        provider2 = _resolve_provider("dummy_provider_cache_mod.DummyProvider")
        assert provider1 is provider2
        assert calls["count"] == 1

        calls["count"] = 0
        _PROVIDER_CACHE.clear()

        barrier = threading.Barrier(5)

        def load_provider_concurrently():
            barrier.wait()
            return _resolve_provider("dummy_provider_cache_mod.DummyProvider")

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(load_provider_concurrently) for _ in range(5)]
            providers = [future.result() for future in futures]

        assert len({id(p) for p in providers}) == 1
        assert calls["count"] == 1
    finally:
        _PROVIDER_CACHE.clear()
