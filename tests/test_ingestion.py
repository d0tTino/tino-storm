import os
import sys
import csv
import types


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from knowledge_storm.utils import QdrantVectorStoreManager  # noqa: E402


class DummyQdrant:
    def __init__(self):
        self.added = []
        self.client = types.SimpleNamespace(close=lambda: None)

    def add_documents(self, documents, batch_size):
        self.added.extend(documents)


def test_create_or_update_vector_store(tmp_path, monkeypatch):
    csv_file = tmp_path / "data.csv"
    with open(csv_file, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["content", "title", "url", "description"]
        )
        writer.writeheader()
        writer.writerow(
            {"content": "foo", "title": "a", "url": "u1", "description": "d"}
        )
        writer.writerow(
            {"content": "bar", "title": "b", "url": "u2", "description": "d"}
        )

    dummy = DummyQdrant()
    monkeypatch.setattr(
        QdrantVectorStoreManager, "_init_offline_vector_db", lambda *a, **k: dummy
    )

    import sys

    if "langchain_huggingface" not in sys.modules:
        mod = types.ModuleType("langchain_huggingface")

        class E:
            def __init__(self, *a, **k):
                pass

        mod.HuggingFaceEmbeddings = E
        sys.modules["langchain_huggingface"] = mod
    if "langchain_text_splitters" not in sys.modules:
        mod = types.ModuleType("langchain_text_splitters")

        class S:
            def __init__(self, *a, **k):
                pass

            def split_documents(self, docs):
                return docs

        mod.RecursiveCharacterTextSplitter = S
        sys.modules["langchain_text_splitters"] = mod

    QdrantVectorStoreManager.create_or_update_vector_store(
        collection_name="c",
        vector_db_mode="offline",
        file_path=str(csv_file),
        content_column="content",
        url_column="url",
        vector_store_path="/tmp",
    )
    assert len(dummy.added) == 2


def test_ingest_emits_event(monkeypatch):
    from tino_storm.ingest import watcher

    events = []

    monkeypatch.setattr(watcher.event_emitter, "emit", lambda e: events.append(e))

    class DummyCollection:
        def __init__(self):
            self.added = []

        def add(self, documents, metadatas, ids):
            self.added.append((documents, metadatas, ids))

    class DummyClient:
        def __init__(self):
            self.collection = DummyCollection()

        def get_or_create_collection(self, name):
            return self.collection

    monkeypatch.setattr(
        watcher.chromadb, "PersistentClient", lambda *a, **k: DummyClient()
    )
    monkeypatch.setattr(watcher.time, "time", lambda: 1.23)

    handler = watcher.VaultIngestHandler("root")

    handler._ingest_text("text", "src.txt", "v1")

    assert handler.client.collection.added
    assert len(events) == 1
    event = events[0]
    from tino_storm.events import ResearchAdded

    assert isinstance(event, ResearchAdded)
    assert event.topic == "v1"
    assert event.information_table["source"] == "src.txt"
    assert event.information_table["doc_id"] == "src.txt-1230"
