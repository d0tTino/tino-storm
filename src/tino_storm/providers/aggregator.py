"""Utilities for aggregating multiple research providers.

This module combines results from several providers while handling failures
gracefully. When a provider raises an exception, the error is logged and a
``ResearchAdded`` event is emitted containing the failing provider name and
error message. Returned results are deduplicated by URL.
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Iterable, List, Dict, Optional, Sequence
from urllib.parse import urlsplit, urlunsplit


from .base import Provider, load_provider
from .registry import provider_registry
from ..search_result import ResearchResult
from ..events import ResearchAdded, event_emitter


def canonical_url(url: str) -> str:
    """Return a canonicalized representation of ``url`` for deduplication.

    The canonical form drops query strings and fragments, lowercases the
    scheme and hostname, and removes any trailing slash from the path. If the
    URL is malformed it is returned unchanged.
    """

    try:
        parts = urlsplit(url)
    except Exception:
        return url

    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower()
    path = parts.path.rstrip("/")
    return urlunsplit((scheme, netloc, path, "", ""))


class ProviderAggregator(Provider):
    """Aggregate results from multiple providers."""

    def __init__(
        self,
        provider_specs: Sequence[str | Provider],
        timeout: Optional[float] = None,
        max_concurrency: Optional[int] = None,
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

        # Default concurrency is the number of providers when not specified
        self.max_concurrency = (
            max_concurrency if max_concurrency is not None else len(self.providers)
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
        actual_timeout = timeout if timeout is not None else self.timeout
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def run_provider(p: Provider) -> List[ResearchResult]:
            async with semaphore:
                return await asyncio.wait_for(
                    p.search_async(
                        query,
                        vaults,
                        k_per_vault=k_per_vault,
                        rrf_k=rrf_k,
                        chroma_path=chroma_path,
                        vault=vault,
                        timeout=actual_timeout,
                    ),
                    timeout=actual_timeout,
                )

        results = await asyncio.gather(
            *(run_provider(p) for p in self.providers),
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
            if url:
                key = canonical_url(url)
                if key not in deduped:
                    deduped[key] = item
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
        with ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(
                    p.search_sync,
                    query,
                    vaults,
                    k_per_vault=k_per_vault,
                    rrf_k=rrf_k,
                    chroma_path=chroma_path,
                    vault=vault,
                    timeout=actual_timeout,
                )
                for p in self.providers
            ]

            for provider, future in zip(self.providers, futures):
                try:
                    r = future.result(timeout=actual_timeout)
                except FuturesTimeoutError:
                    logging.exception(
                        "Provider %s timed out in search_sync", provider
                    )
                    provider_name = getattr(
                        provider, "name", provider.__class__.__name__
                    )
                    event_emitter.emit_sync(
                        ResearchAdded(
                            topic=provider_name,
                            information_table={"error": "timeout"},
                        )
                    )
                except Exception as e:  # pragma: no cover - defensive
                    logging.exception(
                        "Provider %s failed in search_sync", provider
                    )
                    provider_name = getattr(
                        provider, "name", provider.__class__.__name__
                    )
                    event_emitter.emit_sync(
                        ResearchAdded(
                            topic=provider_name,
                            information_table={"error": str(e)},
                        )
                    )
                else:
                    merged.extend(r)

        deduped: Dict[str, ResearchResult] = {}
        for item in merged:
            url = getattr(item, "url", None)
            if url:
                key = canonical_url(url)
                if key not in deduped:
                    deduped[key] = item
        return list(deduped.values())
