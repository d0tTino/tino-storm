import sys
import types
from pathlib import Path
import json
import yaml
import hashlib

import pytest

pytest.importorskip("cryptography")


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


def test_ingest_handler_writes_event(tmp_path, monkeypatch):
    monkeypatch.setattr("watchdog.observers.Observer", _DummyObserver)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    event_dir = tmp_path / "events"
    monkeypatch.setenv("STORM_EVENT_DIR", str(event_dir))
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

    files = list(event_dir.iterdir())
    assert len(files) == 1
    data = json.loads(files[0].read_text())
    assert data["vault"] == vault
    expected_hash = hashlib.sha1("doc:file.pdf".encode()).hexdigest()
    assert data["citation_hashes"] == [expected_hash]


def test_ingest_handler_encrypts(tmp_path, monkeypatch):
    monkeypatch.setattr("watchdog.observers.Observer", _DummyObserver)
    monkeypatch.chdir(tmp_path)
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("STORM_EVENT_DIR", str(tmp_path / "events"))
    cfg_dir = home / ".tino_storm"
    cfg_dir.mkdir(parents=True)
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    key = AESGCM.generate_key(bit_length=256).hex()
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
    assert files and all(p.suffix == ".enc" for p in files)


def test_encrypted_vault_decrypts_on_restart(tmp_path, monkeypatch):
    monkeypatch.setattr("watchdog.observers.Observer", _DummyObserver)
    monkeypatch.chdir(tmp_path)
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    event_dir = tmp_path / "events"
    monkeypatch.setenv("STORM_EVENT_DIR", str(event_dir))
    cfg_dir = home / ".tino_storm"
    cfg_dir.mkdir(parents=True)
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    key = AESGCM.generate_key(bit_length=256).hex()
    (cfg_dir / "config.yaml").write_text(
        f"encrypt_vault: true\nencryption_key: {key}\n"
    )

    vault = "vault"
    vault_dir = Path("research") / vault
    vault_dir.mkdir(parents=True)

    from tino_storm.ingest.watchdog import IngestHandler

    handler = IngestHandler(vault)

    pdf = vault_dir / "file.pdf"
    content = "pdf"
    pdf.write_text(content)
    handler.ingest_file(pdf)

    files = list(handler.storage_dir.iterdir())
    assert any(f.suffix == ".enc" for f in files)

    handler = IngestHandler(vault)

    files = list(handler.storage_dir.iterdir())
    assert all(f.suffix != ".enc" for f in files)
    decrypted = (handler.storage_dir / "index.txt").read_text()
    assert decrypted == "persisted"


def test_encrypt_decrypt_round_trip(tmp_path):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    from tino_storm.ingest.watchdog import _encrypt_dir, _decrypt_dir

    key = AESGCM.generate_key(bit_length=256)
    aesgcm = AESGCM(key)

    file = tmp_path / "file.txt"
    content = b"secret"
    file.write_bytes(content)

    _encrypt_dir(tmp_path, aesgcm)
    enc_files = list(tmp_path.glob("*.enc"))
    assert len(enc_files) == 1

    _decrypt_dir(tmp_path, aesgcm)
    assert file.read_bytes() == content


def test_url_manifest_ingests_threads(tmp_path, monkeypatch):
    monkeypatch.setattr("watchdog.observers.Observer", _DummyObserver)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("STORM_EVENT_DIR", str(tmp_path / "events"))
    vault = "vault"
    vault_dir = Path("research") / vault
    vault_dir.mkdir(parents=True)

    from tino_storm.ingest.watchdog import IngestHandler

    captured = []

    def fake_load(url: str):
        captured.append(url)
        return [{"text": "content"}]

    monkeypatch.setattr(sys.modules["tino_storm.ingest.watchdog"], "load", fake_load)

    handler = IngestHandler(vault)

    manifest = vault_dir / "threads.yaml"
    manifest.write_text(
        yaml.safe_dump(
            {
                "urls": [
                    "https://twitter.com/user/status/1",
                    "https://www.reddit.com/r/test/comments/abc/post/",
                    "https://boards.4chan.org/g/thread/123",
                ]
            }
        )
    )

    handler.ingest_file(manifest)

    assert (handler.storage_dir / "index.txt").exists()
    assert len(captured) == 3


def test_watch_vault_ingests_existing_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("STORM_EVENT_DIR", str(tmp_path / "events"))
    vault = "vault"
    vault_dir = Path("research") / vault
    vault_dir.mkdir(parents=True)

    pdf = vault_dir / "file.pdf"
    pdf.write_text("pdf")

    from tino_storm.ingest.watchdog import watch_vault, IngestHandler

    recorded: list[Path] = []

    def ingest_file(self, path: Path) -> None:
        recorded.append(path)

    monkeypatch.setattr(IngestHandler, "ingest_file", ingest_file, raising=False)

    rec = _RecordingObserver()
    monkeypatch.setattr("tino_storm.ingest.watchdog.Observer", lambda: rec)

    def raise_(*args, **kwargs):
        raise KeyboardInterrupt()

    monkeypatch.setattr("tino_storm.ingest.watchdog.time.sleep", raise_)

    watch_vault(vault)

    assert recorded == [pdf]


def test_json_manifest_ingests_threads(tmp_path, monkeypatch):
    monkeypatch.setattr("watchdog.observers.Observer", _DummyObserver)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("STORM_EVENT_DIR", str(tmp_path / "events"))
    vault = "vault"
    vault_dir = Path("research") / vault
    vault_dir.mkdir(parents=True)

    from tino_storm.ingest.watchdog import IngestHandler

    captured = []

    def fake_load(url: str):
        captured.append(url)
        return [{"text": "content"}]

    monkeypatch.setattr(sys.modules["tino_storm.ingest.watchdog"], "load", fake_load)

    handler = IngestHandler(vault)

    manifest = vault_dir / "threads.json"
    manifest.write_text(
        json.dumps(
            {
                "urls": [
                    "https://twitter.com/user/status/1",
                    "https://www.reddit.com/r/test/comments/abc/post/",
                    "https://boards.4chan.org/g/thread/123",
                ]
            }
        )
    )

    handler.ingest_file(manifest)

    assert (handler.storage_dir / "index.txt").exists()
    assert len(captured) == 3
