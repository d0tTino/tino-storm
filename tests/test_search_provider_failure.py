import pytest

import tino_storm
from tino_storm.events import ResearchAdded, event_emitter
from tino_storm.search import ResearchError, search_sync as search_func


def test_invalid_env_provider_emits_event(monkeypatch):
    monkeypatch.setattr(event_emitter, "_subscribers", {})
    events = []

    def handler(e: ResearchAdded) -> None:
        events.append(e)

    event_emitter.subscribe(ResearchAdded, handler)

    spec = "nonexistent.module.Provider"
    monkeypatch.setenv("STORM_SEARCH_PROVIDER", spec)

    monkeypatch.setattr(tino_storm, "search_sync", search_func)

    with pytest.raises(ResearchError) as exc:
        tino_storm.search_sync("topic", [])

    assert exc.value.provider_spec == spec
    assert len(events) == 1
    event = events[0]
    assert event.topic == spec
    assert event.information_table["error"] == str(exc.value)
