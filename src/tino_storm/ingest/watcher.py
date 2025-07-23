from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

import chromadb
import trafilatura

from ..events import ResearchAdded, event_emitter


class VaultIngestHandler(FileSystemEventHandler):
    """Watch a vault directory and ingest dropped files or URLs."""

    def __init__(self, root: str, chroma_path: Optional[str] = None) -> None:
        self.root = Path(root).expanduser().resolve()
        chroma_root = Path(
            chroma_path
            or os.environ.get(
                "STORM_CHROMA_PATH", Path.home() / ".tino_storm" / "chroma"
            )
        ).expanduser()
        chroma_root.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(chroma_root))
        super().__init__()

    def _ingest_text(self, text: str, source: str, vault: str) -> None:
        collection = self.client.get_or_create_collection(vault)
        # Use timestamp to provide unique ids
        doc_id = f"{source}-{int(time.time()*1000)}"
        collection.add(documents=[text], metadatas=[{"source": source}], ids=[doc_id])
        event_emitter.emit(
            ResearchAdded(
                topic=vault, information_table={"source": source, "doc_id": doc_id}
            )
        )

    def _handle_file(self, path: Path, vault: str) -> None:
        if path.suffix.lower() in {".url", ".urls"}:
            lines = [
                line.strip() for line in path.read_text().splitlines() if line.strip()
            ]
            for url in lines:
                html = trafilatura.fetch_url(url)
                text = trafilatura.extract(html) or ""
                if text:
                    self._ingest_text(text, url, vault)
        else:
            try:
                text = path.read_text(encoding="utf-8")
            except Exception:
                return
            self._ingest_text(text, str(path), vault)

    def on_created(self, event) -> None:  # pragma: no cover - side effects
        if event.is_directory:
            return
        path = Path(event.src_path)
        try:
            rel = path.relative_to(self.root)
        except ValueError:
            return
        vault = rel.parts[0]
        self._handle_file(path, vault)


def start_watcher(
    root: Optional[str] = None, chroma_path: Optional[str] = None
) -> None:
    """Start watching ``root`` for dropped files/URLs."""

    watch_root = Path(
        root or os.environ.get("STORM_VAULT_ROOT", "research")
    ).expanduser()
    handler = VaultIngestHandler(str(watch_root), chroma_path=chroma_path)
    observer = Observer()
    observer.schedule(handler, str(watch_root), recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:  # pragma: no cover - manual termination
        observer.stop()
    observer.join()
