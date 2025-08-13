from __future__ import annotations

import asyncio
import logging
from typing import Iterable, List, Dict, Any, Optional, Sequence

from .base import Provider, load_provider
from .registry import provider_registry


class ProviderAggregator(Provider):
    """Aggregate results from multiple providers."""

    def __init__(self, provider_specs: Sequence[str | Provider]):
        self.providers: List[Provider] = []
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
    ) -> List[Dict[str, Any]]:
        results = await asyncio.gather(
            *[
                p.search_async(
                    query,
                    vaults,
                    k_per_vault=k_per_vault,
                    rrf_k=rrf_k,
                    chroma_path=chroma_path,
                    vault=vault,
                )
                for p in self.providers
            ],
            return_exceptions=True,
        )
        merged: List[Dict[str, Any]] = []
        for provider, r in zip(self.providers, results):
            if isinstance(r, Exception):
                logging.exception("Provider %s failed in search_async", provider)
                continue
            merged.extend(r)
        return merged

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
        merged: List[Dict[str, Any]] = []
        for p in self.providers:
            try:
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
            except Exception:
                logging.exception("Provider %s failed in search_sync", p)
                continue
        return merged
