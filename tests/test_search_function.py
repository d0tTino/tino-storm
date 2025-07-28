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
