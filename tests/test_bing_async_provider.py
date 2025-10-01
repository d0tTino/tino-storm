import asyncio
import os

import httpx

import tino_storm.providers.bing_async  # noqa: F401 ensures provider registration
from tino_storm.providers import provider_registry
from tino_storm.providers.bing_async import BingAsyncProvider
from tino_storm.events import ResearchAdded, event_emitter


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


def test_bing_async_provider_http_error(monkeypatch):
    monkeypatch.setenv("BING_SEARCH_API_KEY", "test-key")

    async def failing_get(*args, **kwargs):
        raise httpx.HTTPError("network boom")

    monkeypatch.setattr(httpx.AsyncClient, "get", failing_get)

    provider = BingAsyncProvider()
    events: list[ResearchAdded] = []

    def handler(event: ResearchAdded) -> None:
        events.append(event)

    event_emitter.subscribe(ResearchAdded, handler)
    try:
        results = asyncio.run(provider.search_async("failing query", []))
    finally:
        event_emitter.unsubscribe(ResearchAdded, handler)

    assert results == []
    assert len(events) == 1
    assert events[0].topic == "failing query"
    assert events[0].information_table["error"] == "network boom"
