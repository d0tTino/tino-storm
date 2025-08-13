import importlib.machinery
import sys
import types

pytesseract = types.ModuleType("pytesseract")
pytesseract.__spec__ = importlib.machinery.ModuleSpec("pytesseract", loader=None)
pytesseract.image_to_string = lambda *a, **k: ""
sys.modules.setdefault("pytesseract", pytesseract)

import asyncio  # noqa: E402

from tino_storm.providers.registry import provider_registry  # noqa: E402


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
