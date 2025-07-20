"""Watch a research vault for new files and index them."""

from __future__ import annotations

import time
import os
from pathlib import Path

from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer
from datetime import datetime, timezone
import yaml
from cryptography.fernet import Fernet

from tino_storm.loaders import load
from tino_storm.events import ResearchAdded, save_event
import json
import hashlib

from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
from llama_index.vector_stores.chroma import ChromaVectorStore


def _load_fernet() -> Fernet | None:
    """Return a :class:`Fernet` instance if vault encryption is enabled."""
    cfg_path = Path("~/.tino_storm/config.yaml").expanduser()
    if not cfg_path.exists():
        return None
    try:
        cfg = yaml.safe_load(cfg_path.read_text()) or {}
    except Exception:  # pragma: no cover - corrupt config
        return None
    if not cfg.get("encrypt_vault"):
        return None
    key = cfg.get("encryption_key")
    if not key:
        key = Fernet.generate_key().decode()
        cfg["encryption_key"] = key
        cfg_path.write_text(yaml.safe_dump(cfg))
    return Fernet(key.encode())


def _encrypt_dir(directory: Path, fernet: Fernet) -> None:
    for file in directory.rglob("*"):
        if file.is_file() and not file.name.endswith(".enc"):
            encrypted = fernet.encrypt(file.read_bytes())
            file.with_suffix(file.suffix + ".enc").write_bytes(encrypted)
            file.unlink()


def _decrypt_dir(directory: Path, fernet: Fernet) -> None:
    for file in directory.rglob("*.enc"):
        decrypted = fernet.decrypt(file.read_bytes())
        file.with_suffix("").write_bytes(decrypted)
        file.unlink()


class IngestHandler(FileSystemEventHandler):
    """Handle new files in a research vault."""

    def __init__(self, vault: str, event_dir: str | Path | None = None):
        self.vault = vault
        self.event_dir = Path(event_dir) if event_dir is not None else Path(
            os.getenv("STORM_EVENT_DIR", "events")
        )
        self.vault_dir = Path("research") / vault
        self.storage_dir = Path("~/.tino_storm/chroma").expanduser() / vault
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._fernet = _load_fernet()
        if self._fernet:
            _decrypt_dir(self.storage_dir, self._fernet)
        vector_store = ChromaVectorStore(persist_path=str(self.storage_dir))
        self.index = VectorStoreIndex.from_vector_store(vector_store)

    def _should_ingest(self, path: Path) -> bool:
        if path.name == "urls.txt":
            return True
        if path.suffix.lower() in {".pdf", ".json", ".txt"}:
            return True
        return False

    def ingest_file(self, path: Path) -> None:
        if not self._should_ingest(path):
            return
        if path.name == "urls.txt":
            urls = [u.strip() for u in path.read_text().splitlines() if u.strip()]
            for url in urls:
                try:
                    records = load(url)
                except Exception as exc:  # pragma: no cover - network
                    print(f"Failed to scrape {url}: {exc}")
                    continue
                out_name = hashlib.sha1(url.encode()).hexdigest()[:8] + ".json"
                out_path = self.vault_dir / out_name
                out_path.write_text(json.dumps(records, default=str))
                self.ingest_file(out_path)
            return
        docs = SimpleDirectoryReader(input_files=[str(path)]).load_data()
        if not docs:
            return
        file_hash = hashlib.sha1(path.read_bytes()).hexdigest()
        ingested_at = datetime.now(timezone.utc).isoformat()
        source_url = str(path)
        if path.suffix.lower() == ".json":
            try:
                data = json.loads(path.read_text())
                if (
                    isinstance(data, list)
                    and data
                    and isinstance(data[0], dict)
                    and "url" in data[0]
                ):
                    source_url = data[0]["url"]
            except Exception:
                pass
        metadata = {
            "file_hash": file_hash,
            "ingested_at": ingested_at,
            "source_url": source_url,
        }
        for node in docs:
            if hasattr(node, "metadata") and isinstance(node.metadata, dict):
                node.metadata.update(metadata)
            else:  # pragma: no cover - depends on reader implementation
                try:
                    node.metadata = metadata
                except Exception:
                    pass
            self.index.insert_nodes([node])
        if self._fernet:
            _encrypt_dir(self.storage_dir, self._fernet)


    def on_created(
        self, event: FileSystemEvent
    ) -> None:  # pragma: no cover - integration
        if event.is_directory:
            return
        self.ingest_file(Path(event.src_path))


def watch_vault(vault: str) -> None:
    """Watch the given research ``vault`` directory for new files and ingest them."""
    watch_path = Path("research") / vault
    watch_path.mkdir(parents=True, exist_ok=True)
    handler = IngestHandler(vault)
    observer = Observer()
    observer.schedule(handler, str(watch_path), recursive=False)
    observer.start()
    try:
        while True:  # pragma: no cover - long running loop
            time.sleep(1)
    except KeyboardInterrupt:  # pragma: no cover - manual stop
        observer.stop()
    observer.join()
