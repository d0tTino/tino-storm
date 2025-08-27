from __future__ import annotations

import asyncio
import logging
from typing import Iterable, List, Optional

from .base import Provider
from .registry import register_provider
from ..events import ResearchAdded, event_emitter
from ..search_result import ResearchResult, as_research_result
from ..ingest import search_vaults


@register_provider("docs_hub")
class DocsHubProvider(Provider):
    """Provider that queries the local Docs/knowledge index."""

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
        """Asynchronously search the local docs index without blocking."""
        try:
            raw_results = await asyncio.to_thread(
                search_vaults,
                query,
                vaults,
                k_per_vault=k_per_vault,
                rrf_k=rrf_k,
                chroma_path=chroma_path,
                vault=vault,
            )
            return [as_research_result(r) for r in raw_results]
        except Exception as e:  # pragma: no cover - network/IO errors
            logging.exception("DocsHubProvider search_async failed")
            await event_emitter.emit(
                ResearchAdded(topic=query, information_table={"error": str(e)})
            )
            return []

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
        """Synchronously search the local docs index."""
        try:
            raw_results = search_vaults(
                query,
                vaults,
                k_per_vault=k_per_vault,
                rrf_k=rrf_k,
                chroma_path=chroma_path,
                vault=vault,
            )
            return [as_research_result(r) for r in raw_results]
        except Exception as e:  # pragma: no cover - network/IO errors
            logging.exception("DocsHubProvider search_sync failed")
            event_emitter.emit_sync(
                ResearchAdded(topic=query, information_table={"error": str(e)})
            )
            return []
