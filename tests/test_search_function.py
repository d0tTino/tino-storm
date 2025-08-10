import asyncio
import importlib

import tino_storm


def test_search_sync(monkeypatch):
    """search() should call search_vaults when no event loop is running."""

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
        ):
            called["args"] = (
                query,
                list(vaults),
                k_per_vault,
                rrf_k,
                chroma_path,
                vault,
            )
            return ["ok"]

    fake_provider = FakeProvider()
    monkeypatch.setattr(
        search_mod, "_resolve_provider", lambda provider=None: fake_provider
    )
    # restore attribute pointing to function after importing module
    tino_storm.search = search_mod.search
    tino_storm.search_async = search_mod.search_async

    result = tino_storm.search("q", ["v"])

    assert result == ["ok"]
    assert called["args"] == ("q", ["v"], 5, 60, None, None)


def test_search_async(monkeypatch):
    """search() should delegate to asyncio.to_thread inside an event loop."""

    search_mod = importlib.import_module("tino_storm.search")
    called = {}

    async def fake_to_thread(func, *a, **k):
        called["thread"] = True
        return func(*a, **k)

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
        ):
            called["sync"] = True
            called["args"] = (
                query,
                list(vaults),
                k_per_vault,
                rrf_k,
                chroma_path,
                vault,
            )
            return ["async"]

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)
    fake_provider = FakeProvider()
    monkeypatch.setattr(
        search_mod, "_resolve_provider", lambda provider=None: fake_provider
    )
    tino_storm.search = search_mod.search
    tino_storm.search_async = search_mod.search_async

    async def _run():
        return await tino_storm.search("q", ["v"])

    result = asyncio.run(_run())

    assert result == ["async"]
    assert called["thread"]
    assert called["args"] == ("q", ["v"], 5, 60, None, None)


def test_search_awaits_provider_coroutine(monkeypatch):
    """search() should await Provider.search_async when defined."""

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
        ):
            called["args"] = (
                query,
                list(vaults),
                k_per_vault,
                rrf_k,
                chroma_path,
                vault,
            )
            return ["awaited"]

        def search_sync(self, *a, **k):
            called["sync"] = True
            return []

    provider_instance = AsyncProvider()
    monkeypatch.setattr(
        search_mod, "_resolve_provider", lambda provider=None: provider_instance
    )
    tino_storm.search = search_mod.search
    tino_storm.search_async = search_mod.search_async

    async def _run():
        return await tino_storm.search("q", ["v"])

    result = asyncio.run(_run())

    assert result == ["awaited"]
    assert called["args"] == ("q", ["v"], 5, 60, None, None)
    assert "sync" not in called


def test_search_without_vaults_uses_default(monkeypatch):
    """search() without vaults should fall back to list_vaults."""

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
        ):
            called["args"] = (
                query,
                list(vaults),
                k_per_vault,
                rrf_k,
                chroma_path,
                vault,
            )
            return ["ok"]

    monkeypatch.setattr(search_mod, "list_vaults", fake_list_vaults)
    fake_provider = FakeProvider()
    monkeypatch.setattr(
        search_mod, "_resolve_provider", lambda provider=None: fake_provider
    )
    tino_storm.search = search_mod.search
    tino_storm.search_async = search_mod.search_async

    result = tino_storm.search("q")

    assert result == ["ok"]
    assert called["list"]
    assert called["args"] == ("q", ["a", "b"], 5, 60, None, None)
