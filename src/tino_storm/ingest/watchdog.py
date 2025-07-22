"""Watch a research vault for new files and index them."""

from __future__ import annotations

import time
import os
from pathlib import Path

from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer
from datetime import datetime, timezone
import yaml
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from tino_storm.loaders import load
from tino_storm.events import ResearchAdded, save_event
import json
import hashlib

from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
from llama_index.vector_stores.chroma import ChromaVectorStore


def _load_aesgcm() -> AESGCM | None:
    """Return an :class:`AESGCM` instance if vault encryption is enabled.

    The configuration file ``~/.tino_storm/config.yaml`` controls vault
    encryption and stores the AES key as a 64 character hex string::

        encrypt_vault: true
        encryption_key: "<64 hex characters>"

    The key is 32 bytes (256 bits).  If missing, a new key is generated and
    written back to the configuration file.
    """
    cfg_path = Path("~/.tino_storm/config.yaml").expanduser()
    if not cfg_path.exists():
        return None
    try:
        cfg = yaml.safe_load(cfg_path.read_text()) or {}
    except Exception:  # pragma: no cover - corrupt config
        return None
    if not cfg.get("encrypt_vault"):
        return None
    key_hex = cfg.get("encryption_key")
    if not key_hex:
        key = AESGCM.generate_key(bit_length=256)
        key_hex = key.hex()
        cfg["encryption_key"] = key_hex
        cfg_path.write_text(yaml.safe_dump(cfg))
    else:
        key = bytes.fromhex(key_hex)
    return AESGCM(key)


def _encrypt_dir(directory: Path, aesgcm: AESGCM) -> None:
    """Encrypt all files within ``directory`` using ``aesgcm``.

    Each file is encrypted with a fresh 96-bit nonce and replaced by a new file
    with an additional ``.enc`` suffix.  The nonce is prepended to the ciphertext
    so :func:`_decrypt_dir` can restore the original contents.
    """
    for file in directory.rglob("*"):
        if file.is_file() and not file.name.endswith(".enc"):
            data = file.read_bytes()
            nonce = os.urandom(12)
            encrypted = nonce + aesgcm.encrypt(nonce, data, None)
            file.with_suffix(file.suffix + ".enc").write_bytes(encrypted)
            file.unlink()


def _decrypt_dir(directory: Path, aesgcm: AESGCM) -> None:
    """Decrypt ``.enc`` files within ``directory`` using ``aesgcm``."""
    for file in directory.rglob("*.enc"):
        data = file.read_bytes()
        nonce, ciphertext = data[:12], data[12:]
        decrypted = aesgcm.decrypt(nonce, ciphertext, None)
        file.with_suffix("").write_bytes(decrypted)
        file.unlink()


_THREAD_DOMAINS = {
    "twitter.com",
    "x.com",
    "reddit.com",
    "4chan.org",
    "4channel.org",
}


def _parse_url_manifest(path: Path) -> list[str] | None:
    """Return a list of thread URLs if ``path`` looks like a manifest."""
    try:
        text = path.read_text()
    except Exception:
        return None

    urls: list[str] | None = None
    if path.suffix.lower() in {".json", ".yaml", ".yml"}:
        try:
            data = yaml.safe_load(text)
        except Exception:
            data = None
        if isinstance(data, dict) and "urls" in data and isinstance(data["urls"], list):
            urls = [str(u) for u in data["urls"]]
        elif isinstance(data, list):
            found: list[str] = []
            for item in data:
                if isinstance(item, str):
                    found.append(item)
                elif isinstance(item, dict) and set(item.keys()) == {"url"}:
                    found.append(str(item["url"]))
                else:
                    found = []
                    break
            if found:
                urls = found
    else:
        urls = [u.strip() for u in text.splitlines() if u.strip()]

    if not urls:
        return None
    filtered = [u for u in urls if any(d in u for d in _THREAD_DOMAINS)]
    return filtered or None


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
        self._aesgcm = _load_aesgcm()
        if self._aesgcm:
            _decrypt_dir(self.storage_dir, self._aesgcm)
        vector_store = ChromaVectorStore(persist_path=str(self.storage_dir))
        self.index = VectorStoreIndex.from_vector_store(vector_store)

    def _should_ingest(self, path: Path) -> bool:
        if path.name == "urls.txt":
            return True
        if path.suffix.lower() in {".pdf", ".json", ".txt", ".yaml", ".yml"}:
            return True
        return False

    def ingest_file(self, path: Path) -> None:
        if not self._should_ingest(path):
            return
        urls = None
        if path.name == "urls.txt":
            urls = [u.strip() for u in path.read_text().splitlines() if u.strip()]
        elif path.suffix.lower() in {".yaml", ".yml", ".json", ".txt"}:
            urls = _parse_url_manifest(path)

        if urls:
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
        meta_path = path.with_suffix(path.suffix + ".meta")
        if meta_path.exists():
            try:
                meta_data = json.loads(meta_path.read_text())
                if isinstance(meta_data, dict):
                    if "authority_rank" in meta_data:
                        metadata["authority_rank"] = meta_data["authority_rank"]
                    elif "authority" in meta_data:
                        metadata["authority_rank"] = meta_data["authority"]
            except Exception:
                pass
        node_hashes: list[str] = []
        for node in docs:
            if hasattr(node, "metadata") and isinstance(node.metadata, dict):
                node.metadata.update(metadata)
            else:  # pragma: no cover - depends on reader implementation
                try:
                    node.metadata = dict(metadata)
                except Exception:
                    pass
            node_hash = None
            try:
                text = getattr(node, "text", str(node))
                node_hash = hashlib.sha1(text.encode()).hexdigest()
                if hasattr(node, "metadata") and isinstance(node.metadata, dict):
                    node.metadata["hash"] = node_hash
            except Exception:
                pass
            self.index.insert_nodes([node])
            if node_hash:
                node_hashes.append(node_hash)
            elif hasattr(node, "metadata") and isinstance(node.metadata, dict):
                h = node.metadata.get("hash")
                if h:
                    node_hashes.append(h)
        try:
            self.index.vector_store.persist()
        except AttributeError:  # pragma: no cover - test stubs
            pass

        if self._aesgcm:
            _encrypt_dir(self.storage_dir, self._aesgcm)
        event = ResearchAdded(
            vault=self.vault,
            path=str(path),
            file_hash=file_hash,
            ingested_at=ingested_at,
            source_url=source_url,
            citation_hashes=node_hashes,
        )
        save_event(event, self.event_dir)


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
    for file in watch_path.iterdir():
        if file.is_file():
            handler.ingest_file(file)
    observer = Observer()
    observer.schedule(handler, str(watch_path), recursive=False)
    observer.start()
    try:
        while True:  # pragma: no cover - long running loop
            time.sleep(1)
    except KeyboardInterrupt:  # pragma: no cover - manual stop
        observer.stop()
    observer.join()
