from __future__ import annotations

import asyncio
from typing import Iterable, List, Dict, Any, Optional

from .base import DefaultProvider, format_bing_items
from ..ingest import search_vaults
from ..retrieval import reciprocal_rank_fusion, score_results, add_posteriors


class ParallelProvider(DefaultProvider):
    """Provider that queries local vaults and Bing concurrently."""

    async def search_async(
        self,
        query: str,
        vaults: Iterable[str],
        *,
        k_per_vault: int = 5,
        rrf_k: int = 60,
        chroma_path: Optional[str] = None,
        vault: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        vault_task = asyncio.to_thread(
            search_vaults,
            query,
            vaults,
            k_per_vault=k_per_vault,
            rrf_k=rrf_k,
            chroma_path=chroma_path,
            vault=vault,
        )
        bing_task = asyncio.to_thread(self._bing_search, query)
        vault_res, bing_res = await asyncio.gather(vault_task, bing_task)

        rankings: List[List[Dict[str, Any]]] = []
        if vault_res:
            rankings.append(vault_res)
        formatted = format_bing_items(bing_res)
        if formatted:
            rankings.append(score_results(formatted))
        if not rankings:
            return []

        fused = reciprocal_rank_fusion(rankings, k=rrf_k)
        return add_posteriors(fused)

    def search_sync(
        self,
        query: str,
        vaults: Iterable[str],
        *,
        k_per_vault: int = 5,
        rrf_k: int = 60,
        chroma_path: Optional[str] = None,
        vault: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return asyncio.run(
            self.search_async(
                query,
                vaults,
                k_per_vault=k_per_vault,
                rrf_k=rrf_k,
                chroma_path=chroma_path,
                vault=vault,
            )
        )
