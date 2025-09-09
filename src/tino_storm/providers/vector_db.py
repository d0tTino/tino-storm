from __future__ import annotations

import asyncio
import logging
from typing import Iterable, List, Optional, Any

from .base import Provider
from .registry import register_provider
from ..events import ResearchAdded, event_emitter
from ..search_result import ResearchResult, as_research_result


@register_provider("vector_db")
class VectorDBProvider(Provider):
    """Provider that queries a vector database using a retrieval helper.

    The provider expects a *retriever* object implementing a ``forward``
    method that accepts a query string and returns an iterable of mappings
    containing ``url`` and ``snippets`` keys (e.g. :class:`~tino_storm.rm.VectorRM`).
    When instantiated without a retriever, the provider will return empty
    results and emit an error event when ``search`` is called.
    """

    def __init__(self, retriever: Any | None = None):
        self.retriever = retriever

    def _ensure_retriever(self) -> Any:
        if self.retriever is None:
            raise RuntimeError("VectorDBProvider requires a retriever instance")
        return self.retriever

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
        """Asynchronously query the vector store without blocking."""

        try:
            retriever = self._ensure_retriever()
            raw_results = await asyncio.to_thread(retriever.forward, query, vault=vault)
            return [as_research_result(r) for r in raw_results]
        except Exception as e:  # pragma: no cover - network/IO errors
            logging.exception("VectorDBProvider search_async failed")
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
        """Synchronously query the vector store."""

        try:
            retriever = self._ensure_retriever()
            raw_results = retriever.forward(query, vault=vault)
            return [as_research_result(r) for r in raw_results]
        except Exception as e:  # pragma: no cover - network/IO errors
            logging.exception("VectorDBProvider search_sync failed")
            event_emitter.emit_sync(
                ResearchAdded(topic=query, information_table={"error": str(e)})
            )
            return []
