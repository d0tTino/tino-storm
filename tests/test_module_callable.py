import importlib

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
