import os
import sys
import types

if "chromadb" not in sys.modules:
    chromadb = types.ModuleType("chromadb")

    class DummyCollection:
        def __init__(self):
            self.docs = []
            self.metadatas = []
            self.ids = []

        def add(self, documents, metadatas=None, ids=None):
            self.docs.extend(documents)
            if metadatas:
                self.metadatas.extend(metadatas)
            if ids:
                self.ids.extend(ids)

    class DummyClient:
        def __init__(self, *a, **k):
            self.collections = {}

        def get_or_create_collection(self, name):
            if name not in self.collections:
                self.collections[name] = DummyCollection()
            return self.collections[name]

    chromadb.PersistentClient = DummyClient
    sys.modules["chromadb"] = chromadb
else:
    DummyClient = sys.modules["chromadb"].PersistentClient

if "watchdog.events" not in sys.modules:
    watchdog = types.ModuleType("watchdog")
    observers_mod = types.ModuleType("watchdog.observers")
    events_mod = types.ModuleType("watchdog.events")

    class FileSystemEventHandler:
        pass

    class DummyObserver:
        def schedule(self, *a, **k):
            pass

        def start(self):
            pass

        def stop(self):
            pass

        def join(self, *a, **k):
            pass

    observers_mod.Observer = DummyObserver
    events_mod.FileSystemEventHandler = FileSystemEventHandler
    watchdog.observers = observers_mod
    watchdog.events = events_mod
    sys.modules["watchdog"] = watchdog
    sys.modules["watchdog.observers"] = observers_mod
    sys.modules["watchdog.events"] = events_mod

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from tino_storm.ingest import VaultIngestHandler  # noqa: E402
from tino_storm.events import event_emitter, ResearchAdded  # noqa: E402


def test_ingest_text_file(monkeypatch, tmp_path):
    # Reset subscribers and capture events
    monkeypatch.setattr(event_emitter, "_subscribers", {})
    events = []
    event_emitter.subscribe(ResearchAdded, lambda e: events.append(e))

    monkeypatch.setattr("chromadb.PersistentClient", DummyClient)

    vault_dir = tmp_path / "topic"
    vault_dir.mkdir()

    handler = VaultIngestHandler(root=str(tmp_path))

    file_path = vault_dir / "note.txt"
    file_path.write_text("hello", encoding="utf-8")

    handler._handle_file(file_path, "topic")

    collection = handler.client.get_or_create_collection("topic")
    assert collection.docs == ["hello"]
    assert len(events) == 1
    assert isinstance(events[0], ResearchAdded)
    assert events[0].topic == "topic"
    assert events[0].information_table["source"] == str(file_path)
