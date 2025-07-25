import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from tino_storm.ingest.search import search_vaults  # noqa: E402


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


def _make_client():
    collections = {
        "v1": DummyCollection(
            [
                ("A snippet", {"source": "docA"}),
                ("B snippet", {"source": "docB"}),
                ("X snippet", {"source": "docX"}),
            ]
        ),
        "v2": DummyCollection(
            [
                ("C snippet", {"source": "docC"}),
                ("A other", {"source": "docA"}),
                ("Y snippet", {"source": "docY"}),
            ]
        ),
    }
    return DummyClient(collections)


def test_search_vaults_rrf(monkeypatch):
    client = _make_client()
    monkeypatch.setattr("chromadb.PersistentClient", lambda *a, **k: client)
    monkeypatch.setattr("tino_storm.ingest.search.get_passphrase", lambda: None)
    # avoid random scoring
    monkeypatch.setattr("tino_storm.ingest.search.score_results", lambda x: x)

    results = search_vaults("q", ["v1", "v2"], k_per_vault=2, rrf_k=5)

    # ensure per-vault limit respected
    assert client.collections["v1"].last_query_kwargs["n_results"] == 2
    assert client.collections["v2"].last_query_kwargs["n_results"] == 2

    # expected RRF order with k=5
    assert [r["url"] for r in results] == ["docA", "docC", "docB"]
