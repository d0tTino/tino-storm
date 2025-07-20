import sys
import types
from pathlib import Path

import pytest


class _FakeVectorStore:
    def __init__(self, persist_path: str):
        self.persist_path = Path(persist_path)

    def persist(self) -> None:
        self.persist_path.mkdir(parents=True, exist_ok=True)
        (self.persist_path / "index.txt").write_text("persisted")


class _FakeStorageContext:
    def __init__(self, store: _FakeVectorStore):
        self.store = store

    def persist(self):
        self.store.persist()


class _FakeIndex:
    def __init__(self, store: _FakeVectorStore | None = None):
        self.nodes = []
        self.vector_store = store or _FakeVectorStore("/tmp")
        self.storage_context = _FakeStorageContext(self.vector_store)

    @classmethod
    def from_vector_store(cls, store: _FakeVectorStore) -> "_FakeIndex":
        return cls(store)

    def insert_nodes(self, nodes):
        self.nodes.extend(nodes)


class _FakeReader:
    def __init__(self, input_files):
        self.input_files = input_files

    def load_data(self):
        return [f"doc:{Path(self.input_files[0]).name}"]


class _DummyObserver:
    def schedule(self, *args, **kwargs):
        pass

    def start(self):
        pass

    def stop(self):
        pass

    def join(self):
        pass


class _RecordingObserver:
    """Record calls made to the Observer methods."""

    def __init__(self):
        self.scheduled = []
        self.started = False
        self.stopped = False
        self.joined = False

    def schedule(self, handler, path, recursive=False):
        self.scheduled.append((handler, path, recursive))

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def join(self):
        self.joined = True


@pytest.fixture(autouse=True)
def stub_dependencies(monkeypatch):
    core_mod = types.ModuleType("llama_index.core")
    core_mod.SimpleDirectoryReader = _FakeReader
    core_mod.VectorStoreIndex = _FakeIndex
    chroma_mod = types.ModuleType("llama_index.vector_stores.chroma")
    chroma_mod.ChromaVectorStore = _FakeVectorStore
    monkeypatch.setitem(sys.modules, "llama_index.core", core_mod)
    monkeypatch.setitem(sys.modules, "llama_index.vector_stores.chroma", chroma_mod)

    observer_mod = types.ModuleType("watchdog.observers")
    observer_mod.Observer = _DummyObserver
    events_mod = types.ModuleType("watchdog.events")
    events_mod.FileSystemEventHandler = object
    events_mod.FileSystemEvent = object
    watchdog_mod = types.ModuleType("watchdog")
    watchdog_mod.observers = observer_mod
    watchdog_mod.events = events_mod
    monkeypatch.setitem(sys.modules, "watchdog", watchdog_mod)
    monkeypatch.setitem(sys.modules, "watchdog.observers", observer_mod)
    monkeypatch.setitem(sys.modules, "watchdog.events", events_mod)

    yield

    for mod in [
        "llama_index.core",
        "llama_index.vector_stores.chroma",
        "watchdog",
        "watchdog.observers",
        "watchdog.events",
    ]:
        sys.modules.pop(mod, None)


def test_ingest_handler_ingests(tmp_path, monkeypatch):
    monkeypatch.setattr("watchdog.observers.Observer", _DummyObserver)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("STORM_EVENT_DIR", str(tmp_path / "events"))
    vault = "vault"
    vault_dir = Path("research") / vault
    vault_dir.mkdir(parents=True)

    from tino_storm.ingest.watchdog import IngestHandler

    monkeypatch.setattr(
        sys.modules["tino_storm.ingest.watchdog"], "load", lambda url: [{"text": "x"}]
    )

    handler = IngestHandler(vault)

    pdf = vault_dir / "file.pdf"
    pdf.write_text("pdf")
    handler.ingest_file(pdf)

    jfile = vault_dir / "file.json"
    jfile.write_text("{}")
    handler.ingest_file(jfile)

    urls = vault_dir / "urls.txt"
    urls.write_text("http://example.com")
    handler.ingest_file(urls)

    assert (handler.storage_dir / "index.txt").exists()


def test_ingest_handler_encrypts(tmp_path, monkeypatch):
    monkeypatch.setattr("watchdog.observers.Observer", _DummyObserver)
    monkeypatch.chdir(tmp_path)
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("STORM_EVENT_DIR", str(tmp_path / "events"))
    cfg_dir = home / ".tino_storm"
    cfg_dir.mkdir(parents=True)
    from cryptography.fernet import Fernet

    key = Fernet.generate_key().decode()
    (cfg_dir / "config.yaml").write_text(
        f"encrypt_vault: true\nencryption_key: {key}\n"
    )


    vault = "vault"
    vault_dir = Path("research") / vault
    vault_dir.mkdir(parents=True)

    from tino_storm.ingest.watchdog import IngestHandler

    handler = IngestHandler(vault)


    pdf = vault_dir / "file.pdf"
    pdf.write_text("pdf")
    handler.ingest_file(pdf)

    files = list(handler.storage_dir.iterdir())
    assert files and (handler.storage_dir / "index.txt.enc") in files
    assert all(p.suffix == ".enc" for p in files)

