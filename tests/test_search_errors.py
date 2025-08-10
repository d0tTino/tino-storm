from tino_storm.search import search, search_async, Provider
from tino_storm.events import event_emitter, ResearchAdded
import asyncio


def test_search_sync_error_emits_event(monkeypatch):
    monkeypatch.setattr(event_emitter, "_subscribers", {})
    events = []
    event_emitter.subscribe(ResearchAdded, lambda e: events.append(e))

    class FailingProvider(Provider):
        def search_sync(self, *a, **k):
            raise RuntimeError("boom")

    result = search("topic", provider=FailingProvider())

    assert result == []
    assert len(events) == 1
    assert events[0].topic == "topic"
    assert events[0].information_table["error"] == "boom"


def test_search_async_error_emits_event(monkeypatch):
    monkeypatch.setattr(event_emitter, "_subscribers", {})
    events = []
    event_emitter.subscribe(ResearchAdded, lambda e: events.append(e))

    class FailingProvider(Provider):
        async def search_async(self, *a, **k):
            raise RuntimeError("boom")

        def search_sync(self, *a, **k):
            raise AssertionError("should not be called")

    async def run():
        return await search_async("topic", provider=FailingProvider())

    result = asyncio.run(run())

    assert result == []
    assert len(events) == 1
    assert events[0].topic == "topic"
    assert events[0].information_table["error"] == "boom"
