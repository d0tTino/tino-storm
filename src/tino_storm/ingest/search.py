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


def search_vaults(
    query: str,
    vaults: Iterable[str],
    *,
    k_per_vault: int = 5,
    rrf_k: int = 60,
    chroma_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Query multiple Chroma namespaces and combine results using RRF."""

    chroma_root = Path(
        chroma_path
        or os.environ.get("STORM_CHROMA_PATH", Path.home() / ".tino_storm" / "chroma")
    ).expanduser()

    passphrase = get_passphrase()
    if passphrase:
        if encrypt_parquet_enabled():
            decrypt_parquet_files(str(chroma_root), passphrase)
            atexit.register(encrypt_parquet_files, str(chroma_root), passphrase)
        client = EncryptedChroma(str(chroma_root), passphrase=passphrase)
    else:
        client = chromadb.PersistentClient(path=str(chroma_root))

    rankings: List[List[Dict[str, Any]]] = []
    for vault in vaults:
        collection = client.get_or_create_collection(vault)
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
