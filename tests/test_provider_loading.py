import sys
import types

import pytest

import asyncio
import tino_storm
from tino_storm.providers import (
    Provider,
    load_provider,
    ParallelProvider,
    DefaultProvider,
)
from tino_storm.search_result import ResearchResult


def test_load_provider_raises(monkeypatch):
    mod = types.ModuleType("dummy_mod")

    class NotProvider:
        pass

    mod.NotProvider = NotProvider
    monkeypatch.setitem(sys.modules, "dummy_mod", mod)

    with pytest.raises(TypeError):
        load_provider("dummy_mod.NotProvider")


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
        ):
            calls["args"] = (
                query,
                list(vaults),
                k_per_vault,
                rrf_k,
                chroma_path,
                vault,
            )
            return [ResearchResult(url="ok", snippets=[], meta={})]

    mod = types.ModuleType("dummy_provider_mod")
    mod.DummyProvider = DummyProvider
    monkeypatch.setitem(sys.modules, "dummy_provider_mod", mod)
    monkeypatch.setenv("STORM_SEARCH_PROVIDER", "dummy_provider_mod.DummyProvider")

    result = tino_storm.search("q", ["v"])

    assert result == [ResearchResult(url="ok", snippets=[], meta={})]
    assert calls["args"] == ("q", ["v"], 5, 60, None, None)


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
        lambda q: [{"url": "bing", "description": "desc", "title": "t"}],
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
        lambda q: [{"url": "u", "description": "d", "title": "t"}],
    )
    results = provider.search_sync("q", [])
    assert results == [
        ResearchResult(url="u", snippets=["d"], meta={"title": "t"}, summary="d")
    ]
