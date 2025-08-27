import importlib.machinery
import sys
import types

pytesseract = types.ModuleType("pytesseract")
pytesseract.__spec__ = importlib.machinery.ModuleSpec("pytesseract", loader=None)
pytesseract.image_to_string = lambda *a, **k: ""
sys.modules.setdefault("pytesseract", pytesseract)

import asyncio  # noqa: E402

from tino_storm.providers.registry import provider_registry  # noqa: E402
from tino_storm.events import event_emitter, ResearchAdded  # noqa: E402


class DummyCollection:
    def __init__(self, results):
        self._results = results
        self.last_query_kwargs = None

    def query(self, query_texts=None, n_results=0, **kwargs):
        self.last_query_kwargs = {"query_texts": query_texts, "n_results": n_results}
        docs = [d for d, _ in self._results][:n_results]
        metas = [m for _, m in self._results][:n_results]
        return {"documents": [docs], "metadatas": [metas]}


class DummyClient:
    def __init__(self, collections):
        self.collections = collections

    def get_or_create_collection(self, name):
        return self.collections[name]


def _setup_index(monkeypatch):
    client = DummyClient(
        {
            "docs_vault": DummyCollection(
                [("A snippet", {"source": "docA"}), ("B snippet", {"source": "docB"})]
            )
        }
    )
    monkeypatch.setattr("chromadb.PersistentClient", lambda *a, **k: client)
    monkeypatch.setattr(
        "tino_storm.ingest.search.get_passphrase", lambda vault=None: None
    )
    monkeypatch.setattr("tino_storm.ingest.search.score_results", lambda x: x)
    return client


def test_docs_hub_provider_registration(monkeypatch):
    monkeypatch.setattr(provider_registry, "_providers", {})
    import importlib
    import tino_storm.providers.docs_hub as docs_hub

    importlib.reload(docs_hub)
    assert isinstance(provider_registry.get("docs_hub"), docs_hub.DocsHubProvider)


def test_docs_hub_provider_search(monkeypatch):
    client = _setup_index(monkeypatch)

    from tino_storm.providers.docs_hub import DocsHubProvider

    provider = DocsHubProvider()
    results = provider.search_sync("q", ["docs_vault"], k_per_vault=2, rrf_k=5)
    assert [r.url for r in results] == ["docA", "docB"]
    assert client.collections["docs_vault"].last_query_kwargs["query_texts"] == ["q"]

    async def run():
        return await provider.search_async("q", ["docs_vault"], k_per_vault=2, rrf_k=5)

    async_results = asyncio.run(run())
    assert [r.url for r in async_results] == ["docA", "docB"]


def test_docs_hub_provider_search_async_non_blocking(monkeypatch):
    client = _setup_index(monkeypatch)

    import tino_storm.providers.docs_hub as docs_hub

    provider = docs_hub.DocsHubProvider()

    original_search_vaults = docs_hub.search_vaults

    def slow_search_vaults(*args, **kwargs):
        import time

        time.sleep(0.05)
        return original_search_vaults(*args, **kwargs)

    monkeypatch.setattr(docs_hub, "search_vaults", slow_search_vaults)

    async def run():
        task = asyncio.create_task(
            provider.search_async("q", ["docs_vault"], k_per_vault=2, rrf_k=5)
        )
        await asyncio.sleep(0.01)
        assert not task.done()
        return await task

    async_results = asyncio.run(run())
    assert [r.url for r in async_results] == ["docA", "docB"]
    assert client.collections["docs_vault"].last_query_kwargs["query_texts"] == ["q"]


def test_docs_hub_provider_search_async_failure(monkeypatch):
    import tino_storm.providers.docs_hub as docs_hub

    provider = docs_hub.DocsHubProvider()

    def raise_err(*_a, **_k):
        raise RuntimeError("boom")

    monkeypatch.setattr(docs_hub, "search_vaults", raise_err)
    monkeypatch.setattr(event_emitter, "_subscribers", {})
    events: list[ResearchAdded] = []

    async def handler(e: ResearchAdded) -> None:
        events.append(e)

    event_emitter.subscribe(ResearchAdded, handler)

    async def run():
        return await provider.search_async("topic", ["vault"])

    results = asyncio.run(run())
    assert results == []
    assert len(events) == 1
    assert events[0].topic == "topic"
    assert events[0].information_table["error"] == "boom"


def test_docs_hub_provider_search_sync_failure(monkeypatch):
    import tino_storm.providers.docs_hub as docs_hub

    provider = docs_hub.DocsHubProvider()

    def raise_err(*_a, **_k):
        raise RuntimeError("boom")

    monkeypatch.setattr(docs_hub, "search_vaults", raise_err)
    monkeypatch.setattr(event_emitter, "_subscribers", {})
    events: list[ResearchAdded] = []

    def handler(e: ResearchAdded) -> None:
        events.append(e)

    event_emitter.subscribe(ResearchAdded, handler)

    results = provider.search_sync("topic", ["vault"])
    assert results == []
    assert len(events) == 1
    assert events[0].topic == "topic"
    assert events[0].information_table["error"] == "boom"
