"""File system watcher for ingesting research files."""

from __future__ import annotations

import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer

from tino_storm.loaders import load
import json
import hashlib

from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
from llama_index.vector_stores.chroma import ChromaVectorStore


class IngestHandler(FileSystemEventHandler):
    """Handle new files in a research vault."""

    def __init__(self, vault: str):
        self.vault = vault
        self.vault_dir = Path("research") / vault
        self.storage_dir = Path("~/.tino_storm/chroma").expanduser() / vault
        self.storage_dir.mkdir(parents=True, exist_ok=True)
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
        for node in docs:
            self.index.insert_nodes([node])
        self.index.vector_store.persist()

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
