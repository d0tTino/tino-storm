import os
import sys
import time
import pytest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from tino_storm.search import search, ResearchError  # noqa: E402


class SlowCollection:
    def query(self, *args, **kwargs):
        time.sleep(0.2)
        return {"documents": [[]], "metadatas": [[]]}


class DummyClient:
    def __init__(self, collection):
        self.collection = collection

    def get_or_create_collection(self, name):
        return self.collection


def test_search_vaults_timeout(monkeypatch):
    coll = SlowCollection()
    client = DummyClient(coll)
    monkeypatch.setattr("chromadb.PersistentClient", lambda *a, **k: client)
    monkeypatch.setattr(
        "tino_storm.ingest.search.get_passphrase", lambda vault=None: None
    )

    with pytest.raises(ResearchError):
        search("q", ["v1"], timeout=0.05)
