import asyncio
import pytest

from tino_storm.providers import DefaultProvider


def test_search_sync_populates_summary_without_model(monkeypatch):
    monkeypatch.delenv("STORM_SUMMARY_MODEL", raising=False)
    monkeypatch.setattr(
        "tino_storm.providers.base.search_vaults",
        lambda *a, **k: [{"url": "u", "snippets": ["s"], "meta": {}}],
    )

    provider = DefaultProvider()
    results = provider.search_sync("q", [])

    assert results[0].summary == "s"


def test_search_sync_uses_summarizer_when_model_set(monkeypatch):
    monkeypatch.setenv("STORM_SUMMARY_MODEL", "model")
    monkeypatch.setattr(
        "tino_storm.providers.base.search_vaults",
        lambda *a, **k: [{"url": "u", "snippets": ["s"], "meta": {}}],
    )

    provider = DefaultProvider()

    def fake_summarizer(_prompt):
        return ["llm summary"]

    monkeypatch.setattr(provider, "_get_summarizer", lambda: fake_summarizer)
    results = provider.search_sync("q", [])

    assert results[0].summary == "llm summary"


@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"], scope="module")
async def test_search_async_populates_summary_without_model(monkeypatch, anyio_backend):
    monkeypatch.delenv("STORM_SUMMARY_MODEL", raising=False)
    monkeypatch.setattr(
        "tino_storm.providers.base.search_vaults",
        lambda *a, **k: [{"url": "u", "snippets": ["s"], "meta": {}}],
    )

    provider = DefaultProvider()
    results = await provider.search_async("q", [])

    assert results[0].summary == "s"


def test_search_sync_summarizes_in_parallel(monkeypatch):
    monkeypatch.delenv("STORM_SUMMARY_MODEL", raising=False)
    monkeypatch.setattr(
        "tino_storm.providers.base.search_vaults",
        lambda *a, **k: [
            {"url": "u1", "snippets": ["s1"], "meta": {}},
            {"url": "u2", "snippets": ["s2"], "meta": {}},
            {"url": "u3", "snippets": ["s3"], "meta": {}},
        ],
    )

    provider = DefaultProvider()
    active = 0
    max_active = 0

    async def fake_summarize(snippets, *, max_chars=200):
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0)
        active -= 1
        return snippets[0]

    monkeypatch.setattr(provider, "_summarize_async", fake_summarize)
    results = provider.search_sync("q", [])

    assert [r.summary for r in results] == ["s1", "s2", "s3"]
    assert max_active > 1


@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"], scope="module")
async def test_search_async_uses_summarizer_when_model_set(monkeypatch, anyio_backend):
    monkeypatch.setenv("STORM_SUMMARY_MODEL", "model")
    monkeypatch.setattr(
        "tino_storm.providers.base.search_vaults",
        lambda *a, **k: [{"url": "u", "snippets": ["s"], "meta": {}}],
    )

    provider = DefaultProvider()

    def fake_summarizer(_prompt):
        return ["llm summary"]

    monkeypatch.setattr(provider, "_get_summarizer", lambda: fake_summarizer)
    results = await provider.search_async("q", [])

    assert results[0].summary == "llm summary"


@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"], scope="module")
async def test_search_async_falls_back_on_summarizer_error(monkeypatch, anyio_backend):
    monkeypatch.setenv("STORM_SUMMARY_MODEL", "model")
    monkeypatch.setattr(
        "tino_storm.providers.base.search_vaults",
        lambda *a, **k: [{"url": "u", "snippets": ["s"], "meta": {}}],
    )

    provider = DefaultProvider()

    def failing_summarizer(_prompt):
        raise RuntimeError("boom")

    monkeypatch.setattr(provider, "_get_summarizer", lambda: failing_summarizer)
    results = await provider.search_async("q", [])

    assert results[0].summary == "s"


@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"], scope="module")
async def test_search_async_summarizes_in_parallel(monkeypatch, anyio_backend):
    monkeypatch.delenv("STORM_SUMMARY_MODEL", raising=False)
    monkeypatch.setattr(
        "tino_storm.providers.base.search_vaults",
        lambda *a, **k: [
            {"url": "u1", "snippets": ["s1"], "meta": {}},
            {"url": "u2", "snippets": ["s2"], "meta": {}},
            {"url": "u3", "snippets": ["s3"], "meta": {}},
        ],
    )

    provider = DefaultProvider()
    active = 0
    max_active = 0

    async def fake_summarize(snippets, *, max_chars=200):
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0)
        active -= 1
        return snippets[0]

    monkeypatch.setattr(provider, "_summarize_async", fake_summarize)
    results = await provider.search_async("q", [])

    assert [r.summary for r in results] == ["s1", "s2", "s3"]
    assert max_active > 1
