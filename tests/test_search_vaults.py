import logging
import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from tino_storm.ingest.search import search_vaults  # noqa: E402
from tino_storm.events import ResearchAdded, event_emitter  # noqa: E402


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
    monkeypatch.setattr(
        "tino_storm.ingest.search.get_passphrase", lambda vault=None: None
    )
    # avoid random scoring
    monkeypatch.setattr("tino_storm.ingest.search.score_results", lambda x: x)

    results = search_vaults("q", ["v1", "v2"], k_per_vault=2, rrf_k=5)

    # ensure per-vault limit respected
    assert client.collections["v1"].last_query_kwargs["n_results"] == 2
    assert client.collections["v2"].last_query_kwargs["n_results"] == 2

    # expected RRF order with k=5
    assert [r["url"] for r in results] == ["docA", "docC", "docB"]


def test_search_vaults_failure_emits_event(monkeypatch, caplog):
    client = _make_client()

    class BoomCollection:
        def query(self, *args, **kwargs):
            raise RuntimeError("boom")

    client.collections["v1"] = BoomCollection()

    monkeypatch.setattr("chromadb.PersistentClient", lambda *a, **k: client)
    monkeypatch.setattr(
        "tino_storm.ingest.search.get_passphrase", lambda vault=None: None
    )
    monkeypatch.setattr("tino_storm.ingest.search.score_results", lambda x: x)
    monkeypatch.setattr(event_emitter, "_subscribers", {})

    events: list[ResearchAdded] = []

    def handler(event: ResearchAdded) -> None:
        events.append(event)

    event_emitter.subscribe(ResearchAdded, handler)

    with caplog.at_level(logging.ERROR):
        results = search_vaults("q", ["v1"], k_per_vault=2, rrf_k=5)

    assert results == []
    assert len(events) == 1
    assert events[0].topic == "q"
    assert events[0].information_table["stage"] == "local"
    assert events[0].information_table["provider"] == "search_vaults"
    assert events[0].information_table["vault"] == "v1"
    assert "boom" in events[0].information_table["error"]
    assert any(
        "search_vaults query failed" in record.getMessage() for record in caplog.records
    )


def test_search_vaults_failure_still_collects_other_vaults(monkeypatch):
    client = _make_client()

    class BoomCollection:
        def query(self, *args, **kwargs):
            raise RuntimeError("boom")

    client.collections["v1"] = BoomCollection()

    monkeypatch.setattr("chromadb.PersistentClient", lambda *a, **k: client)
    monkeypatch.setattr(
        "tino_storm.ingest.search.get_passphrase", lambda vault=None: None
    )
    monkeypatch.setattr("tino_storm.ingest.search.score_results", lambda x: x)

    results = search_vaults("q", ["v1", "v2"], k_per_vault=2, rrf_k=5)

    assert [r["url"] for r in results] == ["docC", "docA"]
