from __future__ import annotations

import asyncio
import logging
from typing import Iterable, List, Dict, Any, Optional

from .base import DefaultProvider, format_bing_items, _run_coroutine_in_new_loop
from .docs_hub import DocsHubProvider
from .registry import register_provider
from ..events import ResearchAdded, event_emitter
from ..ingest import search_vaults
from ..retrieval import reciprocal_rank_fusion, score_results, add_posteriors
from ..search_result import ResearchResult, as_research_result


@register_provider("multi_source")
class MultiSourceProvider(DefaultProvider):
    """Provider that queries local vaults, DocsHub, and Bing in parallel."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.docs_provider = DocsHubProvider()

    async def search_async(
        self,
        query: str,
        vaults: Iterable[str],
        *,
        k_per_vault: int = 5,
        rrf_k: int = 60,
        chroma_path: Optional[str] = None,
        vault: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> List[ResearchResult]:
        vault_task = asyncio.to_thread(
            search_vaults,
            query,
            vaults,
            k_per_vault=k_per_vault,
            rrf_k=rrf_k,
            chroma_path=chroma_path,
            vault=vault,
            timeout=timeout,
        )
        docs_task = self.docs_provider.search_async(
            query,
            vaults,
            k_per_vault=k_per_vault,
            rrf_k=rrf_k,
            chroma_path=chroma_path,
            vault=vault,
            timeout=timeout,
        )
        bing_task = asyncio.to_thread(self._bing_search, query)

        vault_res, docs_res, bing_res = await asyncio.gather(
            vault_task, docs_task, bing_task, return_exceptions=True
        )

        rankings: List[List[Dict[str, Any]]] = []

        for source, res in (
            ("vault", vault_res),
            ("docs", docs_res),
            ("bing", bing_res),
        ):
            if isinstance(res, Exception):
                logging.exception("%s search failed in MultiSourceProvider", source)
                await event_emitter.emit(
                    ResearchAdded(topic=query, information_table={"error": str(res)})
                )
                res = []

            if source == "vault" and res:
                rankings.append(res)
            elif source == "docs" and res:
                formatted_docs: List[Dict[str, Any]] = []
                for r in res:
                    info: Dict[str, Any] = {
                        "url": r.url,
                        "snippets": r.snippets,
                        "meta": r.meta,
                    }
                    if r.summary is not None:
                        info["summary"] = r.summary
                    if r.score is not None:
                        info["score"] = r.score
                    if r.posterior is not None:
                        info["posterior"] = r.posterior
                    formatted_docs.append(info)

                rankings.append(formatted_docs)
            elif source == "bing":
                formatted = format_bing_items(res)
                if formatted:
                    rankings.append(score_results(formatted))

        if not rankings:
            return []

        fused = reciprocal_rank_fusion(rankings, k=rrf_k)
        scored = add_posteriors(fused)
        return [as_research_result(r) for r in scored]

    def search_sync(
        self,
        query: str,
        vaults: Iterable[str],
        *,
        k_per_vault: int = 5,
        rrf_k: int = 60,
        chroma_path: Optional[str] = None,
        vault: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> List[ResearchResult]:
        coroutine = self.search_async(
            query,
            vaults,
            k_per_vault=k_per_vault,
            rrf_k=rrf_k,
            chroma_path=chroma_path,
            vault=vault,
            timeout=timeout,
        )

        return _run_coroutine_in_new_loop(coroutine)
