import tino_storm


def test_module_callable(monkeypatch):
    calls = {}

    def fake_search(query, **kwargs):
        calls["query"] = query
        calls["kwargs"] = kwargs
        return "result"

    monkeypatch.setitem(tino_storm.__dict__, "search", fake_search)

    result = tino_storm("my query", foo="bar")

    assert result == "result"
    assert calls == {"query": "my query", "kwargs": {"foo": "bar"}}
