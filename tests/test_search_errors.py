import asyncio

import pytest

from tino_storm.events import event_emitter, ResearchAdded
from tino_storm.search import ResearchError, Provider, search, search_async


def test_search_sync_error_emits_event(monkeypatch):
    monkeypatch.setattr(event_emitter, "_subscribers", {})
    events = []

    async def handler(e):
        events.append(e)

    event_emitter.subscribe(ResearchAdded, handler)

    class FailingProvider(Provider):
        def search_sync(self, *a, **k):
            raise RuntimeError("boom")

    with pytest.raises(ResearchError):
        search("topic", provider=FailingProvider())

    assert len(events) == 1
    assert events[0].topic == "topic"
    assert events[0].information_table["error"] == "boom"


def test_search_async_error_emits_event(monkeypatch):
    monkeypatch.setattr(event_emitter, "_subscribers", {})
    events = []

    async def handler(e):
        events.append(e)

    event_emitter.subscribe(ResearchAdded, handler)

    class FailingProvider(Provider):
        async def search_async(self, *a, **k):
            raise RuntimeError("boom")

        def search_sync(self, *a, **k):
            raise AssertionError("should not be called")

    async def run():
        await search_async("topic", provider=FailingProvider())

    with pytest.raises(ResearchError):
        asyncio.run(run())

    assert len(events) == 1
    assert events[0].topic == "topic"
    assert events[0].information_table["error"] == "boom"
