from __future__ import annotations

import os
import atexit
from pathlib import Path
from typing import Any, Iterable, List, Dict, Optional

import chromadb

from ..security import (
    get_passphrase,
    encrypt_parquet_enabled,
    decrypt_parquet_files,
    encrypt_parquet_files,
)
from ..security.encrypted_chroma import EncryptedChroma
from ..retrieval.rrf import reciprocal_rank_fusion
from ..retrieval.scoring import score_results
from ..retrieval.bayes import add_posteriors


def list_vaults(root: Optional[str] = None) -> list[str]:
    """Return available vault directories under ``root``.

    If ``root`` is not provided, the ``STORM_VAULT_ROOT`` environment variable is
    consulted. If that is unset, the default ``~/.tino_storm/research`` directory
    is used. Only sub-directories are returned and the result is sorted
    alphabetically.
    """

    root_path = Path(
        root or os.environ.get("STORM_VAULT_ROOT") or Path.home() / ".tino_storm" / "research"
    ).expanduser()

    if not root_path.exists():
        return []

    return sorted(p.name for p in root_path.iterdir() if p.is_dir())


def search_vaults(
    query: str,
    vaults: Iterable[str],
    *,
    k_per_vault: int = 5,
    rrf_k: int = 60,
    chroma_path: Optional[str] = None,
    vault: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Query multiple Chroma namespaces and combine results using RRF."""

    chroma_root = Path(
        chroma_path
        or os.environ.get("STORM_CHROMA_PATH", Path.home() / ".tino_storm" / "chroma")
    ).expanduser()

    def _create_client(passphrase: str | None):
        if passphrase:
            if encrypt_parquet_enabled():
                decrypt_parquet_files(str(chroma_root), passphrase)
                atexit.register(encrypt_parquet_files, str(chroma_root), passphrase)
            return EncryptedChroma(str(chroma_root), passphrase=passphrase)
        return chromadb.PersistentClient(path=str(chroma_root))

    if vault is not None:
        client = _create_client(get_passphrase(vault))
        client_map = {vault: client}
    else:
        client = None
        client_map: dict[str | None, Any] = {}

    rankings: List[List[Dict[str, Any]]] = []
    for vault_name in vaults:
        if vault is not None:
            collection = client.get_or_create_collection(vault_name)
        else:
            pw = get_passphrase(vault_name)
            c = client_map.get(pw)
            if c is None:
                c = _create_client(pw)
                client_map[pw] = c
            collection = c.get_or_create_collection(vault_name)
        try:
            res = collection.query(query_texts=[query], n_results=k_per_vault)
        except Exception:
            res = {"documents": [[]], "metadatas": [[]]}

        docs = res.get("documents", [[]])[0] or []
        metas = res.get("metadatas", [[]])[0] or []

        ranking: List[Dict[str, Any]] = []
        for idx, doc in enumerate(docs):
            meta = metas[idx] if idx < len(metas) else {}
            url = meta.get("source", str(idx))
            ranking.append({"url": url, "snippets": [doc], "meta": meta})
        if ranking:
            rankings.append(score_results(ranking))

    if not rankings:
        return []

    fused = reciprocal_rank_fusion(rankings, k=rrf_k)
    return add_posteriors(fused)
