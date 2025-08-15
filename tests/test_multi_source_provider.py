import asyncio

from tino_storm.providers.multi_source import MultiSourceProvider
from tino_storm.search_result import ResearchResult


def test_multi_source_provider_queries_all_sources(monkeypatch):
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
        "tino_storm.providers.multi_source.search_vaults",
        lambda *a, **k: [{"url": "vault", "snippets": [], "meta": {}}],
    )

    provider = MultiSourceProvider()
    monkeypatch.setattr(
        provider,
        "_bing_search",
        lambda q: [{"url": "bing", "description": "desc", "title": "t"}],
    )

    async def docs_search_async(query, vaults, **kwargs):
        return [ResearchResult(url="docs", snippets=[], meta={})]

    monkeypatch.setattr(provider.docs_provider, "search_async", docs_search_async)

    async def run():
        return await provider.search_async("q", ["v"])

    results = asyncio.run(run())

    assert gathered["count"] == 3
    assert {r.url for r in results} == {"vault", "docs", "bing"}
    bing_result = next(r for r in results if r.url == "bing")
    assert bing_result.snippets == ["desc"]
    assert bing_result.meta["title"] == "t"
