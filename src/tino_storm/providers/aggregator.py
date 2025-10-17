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
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set
from urllib.parse import urlsplit, urlunsplit


from .base import Provider, load_provider, _run_coroutine_in_new_loop
from .registry import provider_registry
from ..retrieval.rrf import reciprocal_rank_fusion
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


def _update_best_metadata(existing: ResearchResult, candidate: ResearchResult) -> None:
    """Merge ``candidate`` metadata into ``existing`` preferring richer fields."""

    existing_score = existing.score if existing.score is not None else float("-inf")
    candidate_score = candidate.score if candidate.score is not None else float("-inf")

    if candidate.summary and (
        not existing.summary
        or len(candidate.summary) > len(existing.summary)
        or candidate_score > existing_score
    ):
        existing.summary = candidate.summary

    if candidate.score is not None and candidate.score > existing_score:
        existing.score = candidate.score

    if candidate.posterior is not None and (
        existing.posterior is None or candidate.posterior > existing.posterior
    ):
        existing.posterior = candidate.posterior

    if candidate.snippets and not existing.snippets:
        existing.snippets = candidate.snippets

    if candidate.meta:
        merged_meta = dict(existing.meta)
        merged_meta.update(candidate.meta)
        existing.meta = merged_meta


def _fuse_results(
    provider_results: Sequence[Sequence[ResearchResult]],
    *,
    limit: Optional[int],
    rrf_k: int,
) -> List[ResearchResult]:
    """Fuse results from multiple providers using Reciprocal Rank Fusion."""

    canonical_to_result: Dict[str, ResearchResult] = {}
    rankings: List[List[Dict[str, Any]]] = []

    for results in provider_results:
        ranking: List[Dict[str, Any]] = []
        seen_in_ranking: Set[str] = set()

        for item in results:
            url = getattr(item, "url", None)
            if not url:
                continue

            key = canonical_url(url)
            existing = canonical_to_result.get(key)
            if existing is None:
                canonical_to_result[key] = item
            else:
                _update_best_metadata(existing, item)

            if key not in seen_in_ranking:
                ranking.append({"url": key})
                seen_in_ranking.add(key)

        if ranking:
            rankings.append(ranking)

    if not canonical_to_result:
        return []

    ordered_keys: List[str]
    if rankings:
        fused = reciprocal_rank_fusion(rankings, k=rrf_k)
        ordered_keys = [entry["url"] for entry in fused if entry.get("url") in canonical_to_result]
    else:  # pragma: no cover - defensive fallback when rankings are empty
        ordered_keys = list(canonical_to_result.keys())

    remaining = [
        key for key in canonical_to_result.keys() if key not in ordered_keys
    ]
    ordered_keys.extend(remaining)

    fused_results = [canonical_to_result[key] for key in ordered_keys]

    if limit is not None and limit >= 0:
        fused_results = fused_results[:limit]

    return fused_results


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
        aggregated: List[List[ResearchResult]] = []
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

            aggregated.append(r)

        limit = min(k_per_vault, rrf_k) if k_per_vault is not None else rrf_k
        return _fuse_results(aggregated, limit=limit, rrf_k=rrf_k)

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

        aggregated: List[List[ResearchResult]] = []
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
                except NotImplementedError:
                    try:
                        coroutine = provider.search_async(
                            query,
                            vaults,
                            k_per_vault=k_per_vault,
                            rrf_k=rrf_k,
                            chroma_path=chroma_path,
                            vault=vault,
                            timeout=actual_timeout,
                        )
                        if actual_timeout is not None:
                            coroutine = asyncio.wait_for(
                                coroutine, timeout=actual_timeout
                            )
                        r = _run_coroutine_in_new_loop(coroutine)
                    except Exception as e:
                        logging.exception(
                            "Provider %s failed in search_sync fallback", provider
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
                        continue
                except FuturesTimeoutError:
                    logging.exception("Provider %s timed out in search_sync", provider)
                    provider_name = getattr(
                        provider, "name", provider.__class__.__name__
                    )
                    event_emitter.emit_sync(
                        ResearchAdded(
                            topic=provider_name,
                            information_table={"error": "timeout"},
                        )
                    )
                    continue
                except Exception as e:  # pragma: no cover - defensive
                    logging.exception("Provider %s failed in search_sync", provider)
                    provider_name = getattr(
                        provider, "name", provider.__class__.__name__
                    )
                    event_emitter.emit_sync(
                        ResearchAdded(
                            topic=provider_name,
                            information_table={"error": str(e)},
                        )
                    )
                    continue
                aggregated.append(r)

        limit = min(k_per_vault, rrf_k) if k_per_vault is not None else rrf_k
        return _fuse_results(aggregated, limit=limit, rrf_k=rrf_k)
