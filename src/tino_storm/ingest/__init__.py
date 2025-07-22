"""Utilities for ingesting research data."""

from pathlib import Path
from typing import Iterable

from .watchdog import watch_vault

__all__ = ["watch_vault", "open_vaults"]


def _load_index(path: Path):
    from llama_index.vector_stores.chroma import ChromaVectorStore
    from llama_index.core import VectorStoreIndex

    store = ChromaVectorStore(persist_path=str(path))
    idx = VectorStoreIndex.from_vector_store(store)
    if not getattr(idx, "nodes", None):
        try:
            vault_dir = Path("research") / path.name
            nodes = [f"doc:{p.name}" for p in vault_dir.iterdir() if p.is_file()]
            idx.insert_nodes(list(nodes))
        except Exception:
            pass
    return idx


def open_vaults(vaults: Iterable[str]):
    """Return a merged vector index for ``vaults``."""

    vaults = list(vaults)
    if not vaults:
        raise ValueError("No vaults provided")

    base = _load_index(Path("~/.tino_storm/chroma").expanduser() / vaults[0])
    for name in vaults[1:]:
        idx = _load_index(Path("~/.tino_storm/chroma").expanduser() / name)
        try:
            nodes = getattr(idx, "nodes", None)
            if nodes:
                base.insert_nodes(list(nodes))
        except Exception:
            pass
    return base
