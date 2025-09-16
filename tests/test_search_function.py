import asyncio
import importlib

import tino_storm
from tino_storm.search_result import ResearchResult


def test_search_sync(monkeypatch):
    """search_sync() should call provider.search_sync in synchronous mode."""

    called = {}

    search_mod = importlib.import_module("tino_storm.search")

    class FakeProvider(search_mod.Provider):
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
            called["args"] = (
                query,
                list(vaults),
                k_per_vault,
                rrf_k,
                chroma_path,
                vault,
                timeout,
            )
            return [ResearchResult(url="ok", snippets=[], meta={})]

    fake_provider = FakeProvider()
    monkeypatch.setattr(
        search_mod, "_resolve_provider", lambda provider=None: fake_provider
    )
    tino_storm.search_sync = search_mod.search_sync

    result = tino_storm.search_sync("q", ["v"])

    assert result == [ResearchResult(url="ok", snippets=[], meta={})]
    assert called["args"] == ("q", ["v"], 5, 60, None, None, None)


def test_search_async(monkeypatch):
    """search() should await the provider's asynchronous implementation."""

    search_mod = importlib.import_module("tino_storm.search")
    called = {}

    class FakeProvider(search_mod.Provider):
        async def search_async(
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
            called["args"] = (
                query,
                list(vaults),
                k_per_vault,
                rrf_k,
                chroma_path,
                vault,
                timeout,
            )
            return [ResearchResult(url="async", snippets=[], meta={})]

        def search_sync(self, *a, **k):  # pragma: no cover - sanity check
            called["sync"] = True
            return []

    fake_provider = FakeProvider()
    monkeypatch.setattr(
        search_mod, "_resolve_provider", lambda provider=None: fake_provider
    )
    tino_storm.search = search_mod.search

    async def _run():
        return await tino_storm.search("q", ["v"])

    result = asyncio.run(_run())

    assert result == [ResearchResult(url="async", snippets=[], meta={})]
    assert called["args"] == ("q", ["v"], 5, 60, None, None, None)
    assert "sync" not in called


def test_search_async_helper(monkeypatch):
    """search_async() should invoke Provider.search_async."""

    search_mod = importlib.import_module("tino_storm.search")
    called = {}

    class AsyncProvider(search_mod.Provider):
        async def search_async(
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
            called["args"] = (
                query,
                list(vaults),
                k_per_vault,
                rrf_k,
                chroma_path,
                vault,
                timeout,
            )
            return [ResearchResult(url="awaited", snippets=[], meta={})]

        def search_sync(self, *a, **k):
            called["sync"] = True
            return []

    provider_instance = AsyncProvider()
    monkeypatch.setattr(
        search_mod, "_resolve_provider", lambda provider=None: provider_instance
    )

    async def _run():
        return await search_mod.search_async("q", ["v"])

    result = asyncio.run(_run())

    assert result == [ResearchResult(url="awaited", snippets=[], meta={})]
    assert called["args"] == ("q", ["v"], 5, 60, None, None, None)
    assert "sync" not in called


def test_search_without_vaults_uses_default(monkeypatch):
    """search_sync() without vaults should fall back to list_vaults."""

    search_mod = importlib.import_module("tino_storm.search")
    called = {}

    def fake_list_vaults():
        called["list"] = True
        return ["a", "b"]

    class FakeProvider(search_mod.Provider):
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
            called["args"] = (
                query,
                list(vaults),
                k_per_vault,
                rrf_k,
                chroma_path,
                vault,
                timeout,
            )
            return [ResearchResult(url="ok", snippets=[], meta={})]

    monkeypatch.setattr(search_mod, "list_vaults", fake_list_vaults)
    fake_provider = FakeProvider()
    monkeypatch.setattr(
        search_mod, "_resolve_provider", lambda provider=None: fake_provider
    )
    tino_storm.search_sync = search_mod.search_sync

    result = tino_storm.search_sync("q")

    assert result == [ResearchResult(url="ok", snippets=[], meta={})]
    assert called["list"]
    assert called["args"] == ("q", ["a", "b"], 5, 60, None, None, None)


def test_search_falls_back_to_asyncio_run(monkeypatch):
    """search_sync() should run provider.search_async via asyncio.run when needed."""

    search_mod = importlib.import_module("tino_storm.search")
    called = {}

    from tino_storm.providers.bing_async import BingAsyncProvider

    provider = BingAsyncProvider()

    async def fake_search_async(*args, **kwargs):
        called["async"] = True
        return [ResearchResult(url="async", snippets=[], meta={})]

    monkeypatch.setattr(provider, "search_async", fake_search_async)
    monkeypatch.setattr(search_mod, "_resolve_provider", lambda provider=None: provider)

    original_run = asyncio.run

    def fake_run(coro):
        called["run"] = True
        return original_run(coro)

    monkeypatch.setattr(asyncio, "run", fake_run)
    tino_storm.search_sync = search_mod.search_sync

    result = tino_storm.search_sync("q", ["v"], provider=provider)

    assert result == [ResearchResult(url="async", snippets=[], meta={})]
    assert called.get("run")
    assert called.get("async")
