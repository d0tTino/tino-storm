from __future__ import annotations

import asyncio
import logging
from typing import Iterable, List, Optional

from .base import Provider
from .registry import register_provider
from ..events import ResearchAdded, event_emitter
from ..search_result import ResearchResult, as_research_result
from ..ingest import search_vaults
from .docs_hub_client import (
    DocsHubClient,
    DocsHubClientError,
    DocsHubClientNotConfigured,
    get_docs_hub_client,
)


@register_provider("docs_hub")
class DocsHubProvider(Provider):
    """Provider that queries a remote Docs Hub or the local knowledge index."""

    def __init__(self, client: Optional[DocsHubClient] = None) -> None:
        self._client = client or get_docs_hub_client()

    @property
    def is_remote_configured(self) -> bool:
        """Return ``True`` when a remote Docs Hub endpoint is configured."""

        return bool(self._client and self._client.is_configured)

    def _tag_origin(self, results: List[ResearchResult], origin: str) -> List[ResearchResult]:
        """Annotate results with the origin used to satisfy the query."""

        for result in results:
            meta = dict(result.meta) if result.meta else {}
            meta.setdefault("docs_hub_origin", origin)
            result.meta = meta
        return results

    async def _emit_error_async(
        self, query: str, error: Exception, stage: str, extra: Optional[dict] = None
    ) -> None:
        information_table = {
            "error": str(error),
            "stage": stage,
            "provider": "docs_hub",
        }
        if extra:
            information_table.update(extra)
        await event_emitter.emit(
            ResearchAdded(topic=query, information_table=information_table)
        )

    def _emit_error_sync(
        self, query: str, error: Exception, stage: str, extra: Optional[dict] = None
    ) -> None:
        information_table = {
            "error": str(error),
            "stage": stage,
            "provider": "docs_hub",
        }
        if extra:
            information_table.update(extra)
        event_emitter.emit_sync(
            ResearchAdded(topic=query, information_table=information_table)
        )

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
        """Asynchronously search Docs Hub, falling back to the local index."""

        remote_info = {}
        if self.is_remote_configured:
            remote_info = {"remote_url": self._client.base_url, "fallback": "local"}
            try:
                remote_results = await self._client.search_async(
                    query,
                    vaults,
                    k_per_vault=k_per_vault,
                    rrf_k=rrf_k,
                    chroma_path=chroma_path,
                    vault=vault,
                    timeout=timeout,
                )
                parsed_results = [as_research_result(r) for r in remote_results]
                return self._tag_origin(parsed_results, "remote")
            except DocsHubClientNotConfigured:
                remote_info = {}
            except DocsHubClientError as exc:
                logging.warning("DocsHubProvider remote search failed: %s", exc)
                await self._emit_error_async(query, exc, "remote", remote_info)
            except Exception as exc:  # pragma: no cover - defensive
                logging.exception("DocsHubProvider remote search failed")
                await self._emit_error_async(query, exc, "remote", remote_info)

        try:
            raw_results = await asyncio.to_thread(
                search_vaults,
                query,
                vaults,
                k_per_vault=k_per_vault,
                rrf_k=rrf_k,
                chroma_path=chroma_path,
                vault=vault,
                timeout=timeout,
            )
            parsed_results = [as_research_result(r) for r in raw_results]
            return self._tag_origin(parsed_results, "local")
        except Exception as exc:  # pragma: no cover - network/IO errors
            logging.exception("DocsHubProvider local search failed")
            await self._emit_error_async(query, exc, "local")
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
        """Synchronously search Docs Hub, falling back to the local index."""

        remote_info = {}
        if self.is_remote_configured:
            remote_info = {"remote_url": self._client.base_url, "fallback": "local"}
            try:
                remote_results = self._client.search(
                    query,
                    vaults,
                    k_per_vault=k_per_vault,
                    rrf_k=rrf_k,
                    chroma_path=chroma_path,
                    vault=vault,
                    timeout=timeout,
                )
                parsed_results = [as_research_result(r) for r in remote_results]
                return self._tag_origin(parsed_results, "remote")
            except DocsHubClientNotConfigured:
                remote_info = {}
            except DocsHubClientError as exc:
                logging.warning("DocsHubProvider remote search failed: %s", exc)
                self._emit_error_sync(query, exc, "remote", remote_info)
            except Exception as exc:  # pragma: no cover - defensive
                logging.exception("DocsHubProvider remote search failed")
                self._emit_error_sync(query, exc, "remote", remote_info)

        try:
            raw_results = search_vaults(
                query,
                vaults,
                k_per_vault=k_per_vault,
                rrf_k=rrf_k,
                chroma_path=chroma_path,
                vault=vault,
                timeout=timeout,
            )
            parsed_results = [as_research_result(r) for r in raw_results]
            return self._tag_origin(parsed_results, "local")
        except Exception as exc:  # pragma: no cover - network/IO errors
            logging.exception("DocsHubProvider local search failed")
            self._emit_error_sync(query, exc, "local")
            return []
