import pytest

from tino_storm.events import ResearchAdded, event_emitter
from tino_storm.search import _resolve_provider, ResearchError


def test_resolve_provider_fallback_on_malformed_spec(monkeypatch):
    monkeypatch.setattr(event_emitter, "_subscribers", {})
    events = []

    async def handler(e):
        events.append(e)

    event_emitter.subscribe(ResearchAdded, handler)

    with pytest.raises(ResearchError) as exc:
        _resolve_provider("malformed-spec")
    assert len(events) == 1
    assert events[0].topic == "malformed-spec"
    assert "error" in events[0].information_table
    assert exc.value.provider_spec == "malformed-spec"


def test_resolve_provider_env_invalid_fallback(monkeypatch):
    monkeypatch.setattr(event_emitter, "_subscribers", {})
    events = []

    async def handler(e):
        events.append(e)

    event_emitter.subscribe(ResearchAdded, handler)

    spec = "anotherbad"
    monkeypatch.setenv("STORM_SEARCH_PROVIDER", spec)
    with pytest.raises(ResearchError) as exc:
        _resolve_provider(None)

    assert len(events) == 1
    assert events[0].topic == spec
    assert "error" in events[0].information_table
    assert exc.value.provider_spec == spec
