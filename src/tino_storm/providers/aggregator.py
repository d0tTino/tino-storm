"""Utilities for aggregating multiple research providers.

This module combines results from several providers while handling failures
gracefully. When a provider raises an exception, the error is logged and a
``ResearchAdded`` event is emitted containing the failing provider name and
error message. Returned results are deduplicated by URL.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Iterable, List, Dict, Optional, Sequence


from .base import Provider, load_provider
from .registry import provider_registry
from ..search_result import ResearchResult
from ..events import ResearchAdded, event_emitter


class ProviderAggregator(Provider):
    """Aggregate results from multiple providers."""

    def __init__(
        self, provider_specs: Sequence[str | Provider], timeout: Optional[float] = None
    ):
        self.providers: List[Provider] = []
        self.timeout = timeout
        for spec in provider_specs:
            if isinstance(spec, Provider):
                self.providers.append(spec)
            else:
                try:
                    self.providers.append(provider_registry.get(spec))
                except KeyError:
                    self.providers.append(load_provider(spec))

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
        actual_timeout = timeout if timeout is not None else self.timeout
        results = await asyncio.gather(
            *[
                asyncio.wait_for(
                    p.search_async(
                        query,
                        vaults,
                        k_per_vault=k_per_vault,
                        rrf_k=rrf_k,
                        chroma_path=chroma_path,
                        vault=vault,
                    ),
                    timeout=actual_timeout,
                )
                for p in self.providers
            ],
            return_exceptions=True,
        )
        merged: List[ResearchResult] = []
        for provider, r in zip(self.providers, results):
            if isinstance(r, Exception):
                logging.exception("Provider %s failed in search_async", provider)
                provider_name = getattr(provider, "name", provider.__class__.__name__)
                await event_emitter.emit(
                    ResearchAdded(
                        topic=provider_name, information_table={"error": str(r)}
                    )
                )
                continue

            merged.extend(r)

        deduped: Dict[str, ResearchResult] = {}
        for item in merged:
            url = getattr(item, "url", None)
            if url and url not in deduped:
                deduped[url] = item
        return list(deduped.values())

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
        actual_timeout = timeout if timeout is not None else self.timeout
        merged: List[ResearchResult] = []
        for p in self.providers:
            try:
                if actual_timeout is None:
                    merged.extend(
                        p.search_sync(
                            query,
                            vaults,
                            k_per_vault=k_per_vault,
                            rrf_k=rrf_k,
                            chroma_path=chroma_path,
                            vault=vault,
                        )
                    )
                else:
                    res = asyncio.run(
                        asyncio.wait_for(
                            asyncio.to_thread(
                                p.search_sync,
                                query,
                                vaults,
                                k_per_vault=k_per_vault,
                                rrf_k=rrf_k,
                                chroma_path=chroma_path,
                                vault=vault,
                            ),
                            timeout=actual_timeout,
                        )
                    )
                    merged.extend(res)
            except Exception as e:
                logging.exception("Provider %s failed in search_sync", p)
                provider_name = getattr(p, "name", p.__class__.__name__)
                event_emitter.emit_sync(
                    ResearchAdded(
                        topic=provider_name, information_table={"error": str(e)}
                    )
                )
                continue

        deduped: Dict[str, ResearchResult] = {}
        for item in merged:
            url = getattr(item, "url", None)
            if url and url not in deduped:
                deduped[url] = item
        return list(deduped.values())
