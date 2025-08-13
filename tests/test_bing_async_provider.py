import asyncio
import os

import httpx

import tino_storm.providers.bing_async  # noqa: F401 ensures provider registration
from tino_storm.providers import provider_registry
from tino_storm.providers.bing_async import BingAsyncProvider


def test_bing_async_provider_fetches(monkeypatch):
    os.environ["BING_SEARCH_API_KEY"] = "test-key"

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Ocp-Apim-Subscription-Key"] == "test-key"
        assert request.url.params["q"] == "test query"
        data = {"webPages": {"value": [{"url": "https://example.com", "snippet": "Example snippet", "name": "Example"}]}}
        return httpx.Response(200, json=data)

    transport = httpx.MockTransport(handler)
    original_async_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx, "AsyncClient", lambda *a, **k: original_async_client(transport=transport)
    )

    provider = provider_registry.get("bing_async")
    results = asyncio.run(provider.search_async("test query", []))
    assert len(results) == 1
    result = results[0]
    assert result.url == "https://example.com"
    assert result.snippets == ["Example snippet"]
    assert result.meta["title"] == "Example"


def test_bing_async_provider_no_key(monkeypatch):
    monkeypatch.delenv("BING_SEARCH_API_KEY", raising=False)
    provider = BingAsyncProvider()
    results = asyncio.run(provider.search_async("irrelevant", []))
    assert results == []
