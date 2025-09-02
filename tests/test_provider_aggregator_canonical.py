import asyncio

from tino_storm.providers.base import Provider
from tino_storm.providers.aggregator import ProviderAggregator, canonical_url
from tino_storm.search_result import ResearchResult


class VariantProviderA(Provider):
    """Return a URL with a query string."""

    name = "variant_a"

    async def search_async(self, query, vaults, **kwargs):
        return [ResearchResult(url="https://example.com/path?a=1&b=2", snippets=[], meta={})]

    def search_sync(self, query, vaults, **kwargs):
        return [ResearchResult(url="https://example.com/path?a=1&b=2", snippets=[], meta={})]


class VariantProviderB(Provider):
    """Return the same URL with a different query string order."""

    name = "variant_b"

    async def search_async(self, query, vaults, **kwargs):
        return [ResearchResult(url="https://example.com/path?b=2&a=1", snippets=[], meta={})]

    def search_sync(self, query, vaults, **kwargs):
        return [ResearchResult(url="https://example.com/path?b=2&a=1", snippets=[], meta={})]


def test_aggregator_canonical_dedupes():
    aggregator = ProviderAggregator([VariantProviderA(), VariantProviderB()])

    async_results = asyncio.run(aggregator.search_async("query", []))
    assert len(async_results) == 1
    assert canonical_url(async_results[0].url) == "https://example.com/path"

    sync_results = aggregator.search_sync("query", [])
    assert len(sync_results) == 1
    assert canonical_url(sync_results[0].url) == "https://example.com/path"
