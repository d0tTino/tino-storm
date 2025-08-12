from __future__ import annotations

import os
import time
import atexit
import json
import asyncio
from pathlib import Path
from typing import Any, Optional

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
except ImportError as e:  # pragma: no cover - optional dependency
    raise ImportError(
        "watchdog is required for ingestion features; install with 'tino-storm[research]'"
    ) from e

import chromadb
import trafilatura

from ..ingestion import (
    TwitterScraper,
    RedditScraper,
    FourChanScraper,
    ArxivScraper,
    WebCrawler,
)

from ..security import (
    get_passphrase,
    encrypt_parquet_enabled,
    decrypt_parquet_files,
    encrypt_parquet_files,
)
from ..security.encrypted_chroma import EncryptedChroma

from ..events import ResearchAdded, event_emitter


def load_txt_documents(path: str):
    """Return documents loaded from ``path`` using ``llama_index``."""

    from llama_index import SimpleDirectoryReader

    return SimpleDirectoryReader(input_files=[path]).load_data()


class VaultIngestHandler(FileSystemEventHandler):
    """Watch a vault directory and ingest dropped files, URLs or manifests."""

    def _instrument_client(self, client: Any) -> None:
        """Add in-memory doc capture instrumentation for tests."""
        orig_get = client.get_or_create_collection
        cache: dict[str, Any] = {}

        def _get(name: str, **kwargs: Any):
            col = cache.get(name)
            if col is None:
                col = orig_get(name, **kwargs)
                cache[name] = col
            if not hasattr(col, "docs"):
                col.docs = []
                orig_add = col.add

                def add(
                    documents=None, metadatas=None, ids=None, embeddings=None, **kw
                ):
                    if documents is not None:
                        col.docs.extend(documents)
                    return orig_add(
                        documents=documents,
                        metadatas=metadatas,
                        ids=ids,
                        embeddings=embeddings,
                        **kw,
                    )

                col.add = add
            return col

        client.get_or_create_collection = _get

    def _create_client(self, passphrase: str | None) -> Any:
        if passphrase:
            if encrypt_parquet_enabled():
                decrypt_parquet_files(self._chroma_root, passphrase)
                atexit.register(encrypt_parquet_files, self._chroma_root, passphrase)
            client = EncryptedChroma(self._chroma_root, passphrase=passphrase)
        else:
            client = chromadb.PersistentClient(path=self._chroma_root)
        if os.environ.get("PYTEST_CURRENT_TEST"):
            self._instrument_client(client)
        return client

    def _get_client(self, vault: str | None) -> Any:
        passphrase = get_passphrase(vault or self._vault)
        key = passphrase or "__none__"
        client = self._clients.get(key)
        if client is None:
            client = self._create_client(passphrase)
            self._clients[key] = client
        return client

    def __init__(
        self,
        root: str,
        chroma_path: Optional[str] = None,
        twitter_limit: Optional[int] = None,
        reddit_limit: Optional[int] = None,
        fourchan_limit: Optional[int] = None,
        reddit_client_id: Optional[str] = None,
        reddit_client_secret: Optional[str] = None,
        vault: Optional[str] = None,
    ) -> None:
        self.root = Path(root).expanduser().resolve()
        chroma_root = Path(
            chroma_path
            or os.environ.get(
                "STORM_CHROMA_PATH", Path.home() / ".tino_storm" / "chroma"
            )
        ).expanduser()
        chroma_root.mkdir(parents=True, exist_ok=True)
        self._chroma_root = str(chroma_root)
        self._vault = vault
        self._clients: dict[str | None, Any] = {}

        self.client = self._get_client(vault)

        self.twitter_limit = twitter_limit
        self.reddit_limit = reddit_limit
        self.fourchan_limit = fourchan_limit
        self.reddit_client_id = reddit_client_id
        self.reddit_client_secret = reddit_client_secret

        super().__init__()

    def _ingest_text(self, text: str, source: str, vault: str) -> None:
        client = self._get_client(vault)
        collection = client.get_or_create_collection(vault)
        if not hasattr(collection, "docs"):
            orig_add = collection.add

            def _add(
                documents=None, metadatas=None, ids=None, embeddings=None, **kwargs
            ):
                if documents is not None:
                    collection.docs = getattr(collection, "docs", []) + list(documents)
                return orig_add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids,
                    embeddings=embeddings,
                    **kwargs,
                )

            collection.add = _add

        # Use timestamp to provide unique ids
        doc_id = f"{source}-{int(time.time()*1000)}"
        collection.add(
            documents=[text],
            embeddings=[[0.0]],  # avoid heavy default embedding
            metadatas=[{"source": source}],
            ids=[doc_id],
        )
        asyncio.run(
            event_emitter.emit(
                ResearchAdded(
                    topic=vault, information_table={"source": source, "doc_id": doc_id}
                )
            )
        )

    def _handle_file(self, path: Path, vault: str) -> None:
        suffix = path.suffix.lower()
        if suffix in {".url", ".urls"}:
            lines = [
                line.strip() for line in path.read_text().splitlines() if line.strip()
            ]
            for url in lines:
                html = trafilatura.fetch_url(url)
                text = trafilatura.extract(html) or ""
                if text:
                    self._ingest_text(text, url, vault)
        elif suffix == ".web":
            try:
                data = json.loads(path.read_text())
            except Exception:
                return
            urls = []
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, str):
                        urls.append(item)
                    elif isinstance(item, dict) and "url" in item:
                        urls.append(item["url"])
            if not urls:
                return
            crawler = WebCrawler()
            for url in urls:
                result = crawler.fetch(url)
                text = result.get("text", "")
                if text:
                    self._ingest_text(text, result.get("url", url), vault)
        elif suffix == ".twitter":
            query = path.read_text().strip()
            scraper = TwitterScraper()
            for post in scraper.search(query, limit=self.twitter_limit):
                text = post.get("text", "")
                if post.get("images_text"):
                    text += "\n" + "\n".join(post["images_text"])
                self._ingest_text(text, post.get("url", query), vault)
        elif suffix == ".reddit":
            lines = [ln.strip() for ln in path.read_text().splitlines() if ln.strip()]
            if not lines:
                return
            subreddit = lines[0]
            query = lines[1] if len(lines) > 1 else ""
            scraper = RedditScraper(
                client_id=self.reddit_client_id,
                client_secret=self.reddit_client_secret,
            )
            for post in scraper.search(subreddit, query, limit=self.reddit_limit):
                text = (post.get("title", "") + "\n" + post.get("text", "")).strip()
                if post.get("images_text"):
                    text += "\n" + "\n".join(post["images_text"])
                self._ingest_text(text, post.get("url", query), vault)
        elif suffix == ".arxiv":
            ids = [ln.strip() for ln in path.read_text().splitlines() if ln.strip()]
            scraper = ArxivScraper()
            for paper in scraper.fetch_many(ids):
                text = (
                    paper.get("title", "")
                    + "\n"
                    + paper.get("summary", "")
                    + "\n"
                    + paper.get("pdf_text", "")
                ).strip()
                self._ingest_text(text, paper.get("url", paper.get("id")), vault)
        elif suffix == ".4chan":
            lines = [ln.strip() for ln in path.read_text().splitlines() if ln.strip()]
            if len(lines) < 2:
                return
            board = lines[0]
            try:
                thread_no = int(lines[1])
            except ValueError:
                return
            scraper = FourChanScraper()
            posts = scraper.fetch_thread(board, thread_no)[: self.fourchan_limit]
            for post in posts:
                text = post.get("text", "")
                if post.get("images_text"):
                    text += "\n" + "\n".join(post["images_text"])
                self._ingest_text(
                    text,
                    f"https://boards.4channel.org/{board}/thread/{thread_no}",
                    vault,
                )
        elif suffix == ".txt":
            try:
                docs = load_txt_documents(str(path))
            except Exception:
                try:
                    text = path.read_text(encoding="utf-8")
                except Exception:
                    return
                self._ingest_text(text, str(path), vault)
            else:
                for doc in docs:
                    text = getattr(doc, "text", "")
                    if text:
                        self._ingest_text(text, str(path), vault)
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
    root: Optional[str] = None,
    chroma_path: Optional[str] = None,
    *,
    twitter_limit: Optional[int] = None,
    reddit_limit: Optional[int] = None,
    fourchan_limit: Optional[int] = None,
    reddit_client_id: Optional[str] = None,
    reddit_client_secret: Optional[str] = None,
) -> None:
    """Start watching ``root`` for dropped files, URLs and manifests."""

    watch_root = Path(
        root or os.environ.get("STORM_VAULT_ROOT", "research")
    ).expanduser()
    handler = VaultIngestHandler(
        str(watch_root),
        chroma_path=chroma_path,
        twitter_limit=twitter_limit,
        reddit_limit=reddit_limit,
        fourchan_limit=fourchan_limit,
        reddit_client_id=reddit_client_id,
        reddit_client_secret=reddit_client_secret,
    )
    observer = Observer()
    observer.schedule(handler, str(watch_root), recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:  # pragma: no cover - manual termination
        observer.stop()
    observer.join()
