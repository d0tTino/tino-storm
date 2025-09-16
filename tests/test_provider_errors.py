import pytest
from tino_storm.events import event_emitter, ResearchAdded
from tino_storm.search import ResearchError, search_sync


def test_bing_error_emits_event(monkeypatch):
    from tino_storm.providers import DefaultProvider

    monkeypatch.setattr(event_emitter, "_subscribers", {})
    events = []

    async def handler(e):
        events.append(e)

    event_emitter.subscribe(ResearchAdded, handler)

    monkeypatch.setattr("tino_storm.providers.base.search_vaults", lambda *a, **k: [])

    class DummyBing:
        def __init__(self, *a, **k):
            pass

        def __call__(self, query):
            raise RuntimeError("boom")

    monkeypatch.setattr("tino_storm.providers.base.BingSearch", DummyBing)

    provider = DefaultProvider()
    result = provider.search_sync("topic", [])
    assert result == []
    assert len(events) == 1
    assert events[0].topic == "topic"
    assert events[0].information_table["error"] == "boom"


def test_yourm_error_emits_event_once(monkeypatch):
    monkeypatch.setattr(event_emitter, "_subscribers", {})
    events = []

    async def handler(e):
        events.append(e)

    event_emitter.subscribe(ResearchAdded, handler)

    monkeypatch.setattr("tino_storm.security.audit.log_request", lambda *a, **k: None)

    def raise_err(*_a, **_k):
        raise RuntimeError("boom")

    monkeypatch.setattr("tino_storm.core.rm.requests.get", raise_err)

    from tino_storm.core.rm import YouRM

    rm = YouRM(ydc_api_key="x")
    result = rm.forward("topic")

    assert result == []
    assert len(events) == 1
    assert events[0].topic == "topic"
    assert events[0].information_table["error"] == "boom"


def test_search_provider_exception_emits_event(monkeypatch):
    monkeypatch.setattr(event_emitter, "_subscribers", {})
    events = []

    async def handler(e):
        events.append(e)

    event_emitter.subscribe(ResearchAdded, handler)

    import sys
    import types

    dummy_providers = types.ModuleType("tino_storm.providers")

    class _Provider:
        def search_sync(self, *a, **k):
            return []

    dummy_providers.Provider = _Provider
    dummy_providers.DefaultProvider = _Provider
    dummy_providers.load_provider = lambda spec: _Provider()
    monkeypatch.setitem(sys.modules, "tino_storm.providers", dummy_providers)

    class StubProvider:
        def search_sync(self, *a, **k):
            raise RuntimeError("boom")

    with pytest.raises(ResearchError):
        search_sync("topic", [], provider=StubProvider())

    assert len(events) == 1
    assert events[0].topic == "topic"
    assert events[0].information_table["error"] == "boom"
