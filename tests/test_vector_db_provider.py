import asyncio

from tino_storm.providers.vector_db import VectorDBProvider
from tino_storm.events import ResearchAdded


class DummyRetriever:
    def __init__(self):
        self.calls = []

    def forward(self, query, vault=None):
        self.calls.append((query, vault))
        return [{"url": "u", "snippets": ["s"], "meta": {"title": "t"}}]


def test_basic_search_sync_and_async():
    retriever = DummyRetriever()
    provider = VectorDBProvider(retriever)

    sync_res = provider.search_sync("q", [], vault="vault1")
    assert len(sync_res) == 1
    assert sync_res[0].url == "u"

    async_res = asyncio.run(provider.search_async("q", [], vault="vault2"))
    assert len(async_res) == 1
    assert async_res[0].url == "u"

    assert retriever.calls == [("q", "vault1"), ("q", "vault2")]


def test_error_handling(monkeypatch):
    class BoomRetriever:
        def forward(self, query, vault=None):
            raise RuntimeError("boom")

    events = []

    def record(event):
        events.append(event)

    monkeypatch.setattr(
        "tino_storm.providers.vector_db.event_emitter.emit_sync",
        record,
    )

    provider = VectorDBProvider(BoomRetriever())
    res = provider.search_sync("bad", [], vault="vault1")
    assert res == []

    assert len(events) == 1
    assert isinstance(events[0], ResearchAdded)
    assert events[0].topic == "bad"
    assert "boom" in events[0].information_table["error"]
