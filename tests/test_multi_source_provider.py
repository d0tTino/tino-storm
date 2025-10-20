import asyncio

from tino_storm.events import ResearchAdded, event_emitter
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
    provider.docs_provider._client = type("Client", (), {"is_configured": True})()
    monkeypatch.setattr(
        provider,
        "_bing_search",
        lambda *args, **kwargs: [
            {"url": "bing", "description": "desc", "title": "t"}
        ],
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
    assert bing_result.meta["source"] == "bing"
    vault_result = next(r for r in results if r.url == "vault")
    assert vault_result.meta["source"] == "vault"
    docs_result = next(r for r in results if r.url == "docs")
    assert docs_result.meta["source"] == "docs_hub"


def test_multi_source_provider_handles_source_failure(monkeypatch):
    monkeypatch.setattr(event_emitter, "_subscribers", {})
    events: list[ResearchAdded] = []

    async def handler(e: ResearchAdded) -> None:
        events.append(e)

    event_emitter.subscribe(ResearchAdded, handler)

    async def fake_to_thread(func, *a, **k):
        return func(*a, **k)

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(
        "tino_storm.providers.multi_source.search_vaults",
        lambda *a, **k: [{"url": "vault", "snippets": [], "meta": {}}],
    )

    provider = MultiSourceProvider()
    provider.docs_provider._client = type("Client", (), {"is_configured": True})()

    def raise_bing(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(provider, "_bing_search", raise_bing)

    async def docs_search_async(query, vaults, **kwargs):
        return [ResearchResult(url="docs", snippets=[], meta={})]

    monkeypatch.setattr(provider.docs_provider, "search_async", docs_search_async)

    async def run():
        return await provider.search_async("q", ["v"])

    results = asyncio.run(run())

    assert {r.url for r in results} == {"vault", "docs"}
    assert len(events) == 1
    assert events[0].topic == "q"
    assert events[0].information_table["error"] == "boom"
    for result in results:
        if result.url == "vault":
            assert result.meta["source"] == "vault"
        elif result.url == "docs":
            assert result.meta["source"] == "docs_hub"


def test_multi_source_provider_propagates_timeout(monkeypatch):
    async def fake_to_thread(func, *a, **k):
        return func(*a, **k)

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(
        "tino_storm.providers.multi_source.search_vaults",
        lambda *a, **k: [{"url": "vault", "snippets": [], "meta": {}}],
    )

    provider = MultiSourceProvider()
    provider.docs_provider._client = type("Client", (), {"is_configured": True})()

    captured_kwargs: dict[str, object] = {}

    def capture_bing(*_args, **kwargs):
        captured_kwargs.update(kwargs)
        return []

    monkeypatch.setattr(provider, "_bing_search", capture_bing)

    async def docs_search_async(query, vaults, **kwargs):
        return [ResearchResult(url="docs", snippets=[], meta={})]

    monkeypatch.setattr(provider.docs_provider, "search_async", docs_search_async)

    async def run():
        return await provider.search_async("q", ["v"], timeout=42.0)

    asyncio.run(run())

    assert captured_kwargs["timeout"] == 42.0


def test_multi_source_provider_skips_duplicate_local_search(monkeypatch):
    call_count = 0

    async def fake_to_thread(func, *a, **k):
        return func(*a, **k)

    def fake_search_vaults(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return [{"url": "vault", "snippets": [], "meta": {}}]

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(
        "tino_storm.providers.multi_source.search_vaults", fake_search_vaults
    )
    monkeypatch.setattr("tino_storm.providers.docs_hub.search_vaults", fake_search_vaults)

    provider = MultiSourceProvider()
    provider.docs_provider._client = None

    monkeypatch.setattr(provider, "_bing_search", lambda q: [])

    async def run():
        return await provider.search_async("query", ["vault"])

    results = asyncio.run(run())

    assert call_count == 1
    assert {r.url for r in results} == {"vault"}
    assert results[0].meta["source"] == "docs_hub"


def test_multi_source_provider_search_sync_in_running_loop(monkeypatch):
    async def fake_to_thread(func, *a, **k):
        return func(*a, **k)

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(
        "tino_storm.providers.multi_source.search_vaults",
        lambda *a, **k: [{"url": "vault", "snippets": [], "meta": {}}],
    )

    provider = MultiSourceProvider()
    provider.docs_provider._client = type("Client", (), {"is_configured": True})()
    monkeypatch.setattr(
        provider,
        "_bing_search",
        lambda *args, **kwargs: [
            {"url": "bing", "description": "desc", "title": "t"}
        ],
    )

    async def docs_search_async(query, vaults, **kwargs):
        return [ResearchResult(url="docs", snippets=[], meta={})]

    monkeypatch.setattr(provider.docs_provider, "search_async", docs_search_async)

    async def run_sync_call():
        # Ensure an event loop is running before invoking the synchronous API.
        asyncio.get_running_loop()
        return provider.search_sync("q", ["v"])

    results = asyncio.run(run_sync_call())

    assert {r.url for r in results} == {"vault", "docs", "bing"}
    for result in results:
        if result.url == "vault":
            assert result.meta["source"] == "vault"
        elif result.url == "docs":
            assert result.meta["source"] == "docs_hub"
        elif result.url == "bing":
            assert result.meta["source"] == "bing"
