import requests
import pytest

from tino_storm.core.rm import BingSearch, YouRM
from tino_storm.events import ResearchAdded, event_emitter


def test_yourm_timeout_emits_event(monkeypatch):
    monkeypatch.setattr(event_emitter, "_subscribers", {})
    events = []

    async def handler(e):
        events.append(e)

    event_emitter.subscribe(ResearchAdded, handler)

    def mock_get(*a, **k):
        raise requests.Timeout("boom")

    monkeypatch.setattr(requests, "get", mock_get)

    rm = YouRM(ydc_api_key="fake")

    with pytest.raises(requests.Timeout):
        rm.forward("topic")

    assert len(events) == 1
    assert events[0].topic == "topic"
    assert events[0].information_table["error"] == "boom"


def test_bing_timeout_emits_event(monkeypatch):
    monkeypatch.setattr(event_emitter, "_subscribers", {})
    events = []

    async def handler(e):
        events.append(e)

    event_emitter.subscribe(ResearchAdded, handler)

    def mock_get(*a, **k):
        raise requests.Timeout("boom")

    monkeypatch.setattr(requests, "get", mock_get)

    rm = BingSearch(bing_search_api_key="fake")

    result = rm.forward("topic")

    assert result == []
    assert len(events) == 1
    assert events[0].topic == "topic"
    assert events[0].information_table["error"] == "boom"

