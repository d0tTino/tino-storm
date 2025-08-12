"""Utilities for ingesting external resources into Chroma collections."""

from pathlib import Path
from typing import Optional

try:
    from .watcher import start_watcher, VaultIngestHandler, load_txt_documents
except ImportError as e:  # pragma: no cover - optional dependency
    raise ImportError(
        "watchdog is required for ingestion features; install with 'tino-storm[research]'"
    ) from e
from .search import search_vaults


def ingest_path(
    path: str,
    vault: str,
    *,
    root: Optional[str] = None,
    chroma_path: Optional[str] = None,
    twitter_limit: Optional[int] = None,
    reddit_limit: Optional[int] = None,
    fourchan_limit: Optional[int] = None,
    reddit_client_id: Optional[str] = None,
    reddit_client_secret: Optional[str] = None,
) -> None:
    """Ingest a file or manifest into ``vault``.

    Parameters mirror :class:`~VaultIngestHandler` so ingestion can be
    triggered programmatically, e.g. from the ``/ingest`` API endpoint.
    """

    handler = VaultIngestHandler(
        root or str(Path(path).expanduser().parent),
        chroma_path=chroma_path,
        twitter_limit=twitter_limit,
        reddit_limit=reddit_limit,
        fourchan_limit=fourchan_limit,
        reddit_client_id=reddit_client_id,
        reddit_client_secret=reddit_client_secret,
        vault=vault,
    )
    handler._handle_file(Path(path).expanduser(), vault)


__all__ = [
    "start_watcher",
    "VaultIngestHandler",
    "ingest_path",
    "search_vaults",
    "load_txt_documents",
]
