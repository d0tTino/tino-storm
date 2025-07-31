from tino_storm.providers import DefaultProvider
from tino_storm.events import event_emitter, ResearchAdded


def test_bing_error_emits_event(monkeypatch):
    monkeypatch.setattr(event_emitter, "_subscribers", {})
    events = []
    event_emitter.subscribe(ResearchAdded, lambda e: events.append(e))

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
    event_emitter.subscribe(ResearchAdded, lambda e: events.append(e))

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
