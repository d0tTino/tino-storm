"""Utilities for ingesting external resources into Chroma collections."""

from pathlib import Path
from typing import Optional

from .search import search_vaults

WATCHDOG_INSTALL_HINT = (
    "watchdog is required for ingestion features; install with 'tino-storm[research]'"
)


class _WatchdogProxy:
    """Proxy returned when optional watchdog dependency is unavailable."""

    __slots__ = (
        "_name",
        "__name__",
        "__qualname__",
        "__tino_missing_dependency__",
        "__tino_missing_dependency_message__",
    )

    def __init__(self, name: str) -> None:
        self._name = name
        self.__name__ = name
        self.__qualname__ = name
        self.__tino_missing_dependency__ = "watchdog"
        self.__tino_missing_dependency_message__ = WATCHDOG_INSTALL_HINT

    def _raise(self) -> None:
        raise ImportError(self.__tino_missing_dependency_message__)

    def __getattr__(self, _attr: str) -> None:
        self._raise()

    def __call__(self, *args: object, **kwargs: object) -> None:
        self._raise()

    def __repr__(self) -> str:
        return f"<Missing watchdog proxy for {self._name}>"


try:
    from .watcher import start_watcher, VaultIngestHandler, load_txt_documents
except ImportError as exc:  # pragma: no cover - optional dependency
    if "watchdog is required" not in str(exc):
        raise
    start_watcher = _WatchdogProxy("start_watcher")
    VaultIngestHandler = _WatchdogProxy("VaultIngestHandler")
    load_txt_documents = _WatchdogProxy("load_txt_documents")


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
