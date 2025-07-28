import asyncio
import importlib

import tino_storm


def test_search_sync(monkeypatch):
    """search() should call search_vaults when no event loop is running."""

    called = {}

    def fake_search_vaults(
        query, vaults, *, k_per_vault=5, rrf_k=60, chroma_path=None, vault=None
    ):
        called["args"] = (query, list(vaults), k_per_vault, rrf_k, chroma_path, vault)
        return ["ok"]

    search_mod = importlib.import_module("tino_storm.search")
    monkeypatch.setattr(search_mod, "search_vaults", fake_search_vaults)
    # restore attribute pointing to function after importing module
    tino_storm.search = search_mod.search
    tino_storm.search_async = search_mod.search_async

    result = tino_storm.search("q", ["v"])

    assert result == ["ok"]
    assert called["args"] == ("q", ["v"], 5, 60, None, None)


def test_search_async(monkeypatch):
    """search() should delegate to asyncio.to_thread inside an event loop."""

    called = {}

    async def fake_to_thread(func, *a, **k):
        called["thread"] = True
        return func(*a, **k)

    def fake_search_vaults(
        query, vaults, *, k_per_vault=5, rrf_k=60, chroma_path=None, vault=None
    ):
        called["args"] = (query, list(vaults), k_per_vault, rrf_k, chroma_path, vault)
        return ["async"]

    search_mod = importlib.import_module("tino_storm.search")
    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(search_mod, "search_vaults", fake_search_vaults)
    tino_storm.search = search_mod.search
    tino_storm.search_async = search_mod.search_async

    async def _run():
        return await tino_storm.search("q", ["v"])

    result = asyncio.run(_run())

    assert result == ["async"]
    assert called["thread"]
    assert called["args"] == ("q", ["v"], 5, 60, None, None)
