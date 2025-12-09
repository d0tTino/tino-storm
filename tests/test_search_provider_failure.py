import pytest

import tino_storm
from tino_storm.events import ResearchAdded, event_emitter
from tino_storm.search import ResearchError, SearchResults, search_sync as search_func


def test_invalid_env_provider_emits_event(monkeypatch):
    monkeypatch.setattr(event_emitter, "_subscribers", {})
    events = []

    def handler(e: ResearchAdded) -> None:
        events.append(e)

    event_emitter.subscribe(ResearchAdded, handler)

    spec = "nonexistent.module.Provider"
    monkeypatch.setenv("STORM_SEARCH_PROVIDER", spec)

    monkeypatch.setattr(tino_storm, "search_sync", search_func)

    results = tino_storm.search_sync("topic", [])

    assert isinstance(results, SearchResults)
    assert results == []
    assert len(results.errors) == 1
    error_meta = results.errors[0]
    assert error_meta["provider"] == spec
    assert "error" in error_meta
    assert len(events) == 2
    spec_event, query_event = events
    assert spec_event.topic == spec
    assert query_event.topic == "topic"
    assert spec_event.information_table["error"] == error_meta["error"]
    assert query_event.information_table["error"] == error_meta["error"]


def test_invalid_env_provider_can_raise(monkeypatch):
    monkeypatch.setattr(event_emitter, "_subscribers", {})
    events = []

    def handler(e: ResearchAdded) -> None:
        events.append(e)

    event_emitter.subscribe(ResearchAdded, handler)

    spec = "nonexistent.module.Provider"
    monkeypatch.setenv("STORM_SEARCH_PROVIDER", spec)

    monkeypatch.setattr(tino_storm, "search_sync", search_func)

    with pytest.raises(ResearchError) as exc:
        tino_storm.search_sync("topic", [], raise_on_error=True)

    assert exc.value.provider_spec == spec
    assert len(events) == 2
