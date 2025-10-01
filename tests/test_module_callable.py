import importlib

import pytest

import tino_storm


def test_module_callable(monkeypatch):
    calls = {}

    def fake_search(query, **kwargs):
        calls["query"] = query
        calls["kwargs"] = kwargs
        return "result"

    search_mod = importlib.import_module("tino_storm.search")
    monkeypatch.setattr(search_mod, "search_sync", fake_search)

    result = tino_storm("my query", foo="bar")

    assert result == "result"
    assert calls == {"query": "my query", "kwargs": {"foo": "bar"}}


@pytest.mark.parametrize("anyio_backend", ["asyncio"], scope="module")
@pytest.mark.anyio
async def test_module_callable_async(monkeypatch, anyio_backend):
    calls = {}

    async def fake_search(query, **kwargs):
        calls["query"] = query
        calls["kwargs"] = kwargs
        return "async result"

    def fake_search_sync(*args, **kwargs):
        raise AssertionError("search_sync should not be used when an event loop is running")

    search_mod = importlib.import_module("tino_storm.search")
    monkeypatch.setattr(search_mod, "search", fake_search)
    monkeypatch.setattr(search_mod, "search_sync", fake_search_sync)

    result = await tino_storm("async query", foo="baz")

    assert result == "async result"
    assert calls == {"query": "async query", "kwargs": {"foo": "baz"}}
