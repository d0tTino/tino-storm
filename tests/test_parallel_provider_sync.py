import asyncio

from tino_storm.providers.parallel import ParallelProvider


def test_parallel_provider_search_sync_inside_event_loop(monkeypatch):
    monkeypatch.setattr(
        "tino_storm.providers.parallel.search_vaults", lambda *args, **kwargs: []
    )

    provider = ParallelProvider()
    monkeypatch.setattr(provider, "_bing_search", lambda query: [])

    async def invoke_search_sync():
        return provider.search_sync("query", ["vault"])

    results = asyncio.run(invoke_search_sync())

    assert results == []
