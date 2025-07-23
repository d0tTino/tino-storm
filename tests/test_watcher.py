import sys
import types

# Provide a lightweight stub for chromadb so the module can be imported
if "chromadb" not in sys.modules:
    chroma = types.ModuleType("chromadb")

    class PersistentClient:
        def __init__(self, *a, **k):
            pass

        def get_or_create_collection(self, *a, **k):
            return types.SimpleNamespace()

    chroma.PersistentClient = PersistentClient
    sys.modules["chromadb"] = chroma

    api_mod = types.ModuleType("chromadb.api")

    class Collection:
        pass

    api_mod.Collection = Collection
    sys.modules["chromadb.api"] = api_mod

    config_mod = types.ModuleType("chromadb.config")

    class Settings:
        def __init__(self, **kwargs):
            pass

    config_mod.Settings = Settings
    sys.modules["chromadb.config"] = config_mod

if "watchdog.events" not in sys.modules:
    events_mod = types.ModuleType("watchdog.events")

    class FileSystemEventHandler:
        pass

    events_mod.FileSystemEventHandler = FileSystemEventHandler
    watchdog_mod = sys.modules.setdefault("watchdog", types.ModuleType("watchdog"))
    watchdog_mod.events = events_mod
    sys.modules["watchdog.events"] = events_mod

if "watchdog.observers" not in sys.modules:
    observers_mod = types.ModuleType("watchdog.observers")

    class Observer:
        def schedule(self, *a, **k):
            pass

        def start(self):
            pass

        def stop(self):
            pass

        def join(self, *a, **k):
            pass

    observers_mod.Observer = Observer
    watchdog_mod = sys.modules.setdefault("watchdog", types.ModuleType("watchdog"))
    watchdog_mod.observers = observers_mod
    sys.modules["watchdog.observers"] = observers_mod

from tino_storm.ingest.watcher import VaultIngestHandler
from tino_storm.security.encrypted_chroma import EncryptedChroma


def test_handler_uses_encrypted_chroma(tmp_path, monkeypatch):
    monkeypatch.setattr("tino_storm.ingest.watcher.get_passphrase", lambda: "pw")
    handler = VaultIngestHandler(str(tmp_path))
    assert isinstance(handler.client, EncryptedChroma)
