"""Lightweight adapter for TaskCascadence orchestrations.

This module re-exports the minimal search helpers without pulling in the CLI
stack, making it safe to import as a plugin in orchestration environments.
"""

from __future__ import annotations

import asyncio
from typing import Iterable, List, Optional

from .search import search as _search
from .search import search_async as _search_async
from .search import search_sync as _search_sync
from .search_result import ResearchResult

__all__ = [
    "adapter",
    "CascadenceAdapter",
    "search",
    "search_async",
    "search_sync",
]


class CascadenceAdapter:
    """Thin wrapper exposing the TaskCascadence call/search surface."""

    def __call__(
        self,
        query: str,
        vaults: Iterable[str] | None = None,
        *,
        k_per_vault: int = 5,
        rrf_k: int = 60,
        chroma_path: Optional[str] = None,
        vault: Optional[str] = None,
        provider=None,
        timeout: Optional[float] = None,
        raise_on_error: bool = False,
    ):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return _search_sync(
                query,
                vaults,
                k_per_vault=k_per_vault,
                rrf_k=rrf_k,
                chroma_path=chroma_path,
                vault=vault,
                provider=provider,
                timeout=timeout,
                raise_on_error=raise_on_error,
            )
        return _search(
            query,
            vaults,
            k_per_vault=k_per_vault,
            rrf_k=rrf_k,
            chroma_path=chroma_path,
            vault=vault,
            provider=provider,
            timeout=timeout,
            raise_on_error=raise_on_error,
        )

    async def search(
        self,
        query: str,
        vaults: Iterable[str] | None = None,
        *,
        k_per_vault: int = 5,
        rrf_k: int = 60,
        chroma_path: Optional[str] = None,
        vault: Optional[str] = None,
        provider=None,
        timeout: Optional[float] = None,
        raise_on_error: bool = False,
    ) -> List[ResearchResult]:
        return await _search(
            query,
            vaults,
            k_per_vault=k_per_vault,
            rrf_k=rrf_k,
            chroma_path=chroma_path,
            vault=vault,
            provider=provider,
            timeout=timeout,
            raise_on_error=raise_on_error,
        )

    def search_sync(
        self,
        query: str,
        vaults: Iterable[str] | None = None,
        *,
        k_per_vault: int = 5,
        rrf_k: int = 60,
        chroma_path: Optional[str] = None,
        vault: Optional[str] = None,
        provider=None,
        timeout: Optional[float] = None,
        raise_on_error: bool = False,
    ) -> List[ResearchResult]:
        return _search_sync(
            query,
            vaults,
            k_per_vault=k_per_vault,
            rrf_k=rrf_k,
            chroma_path=chroma_path,
            vault=vault,
            provider=provider,
            timeout=timeout,
            raise_on_error=raise_on_error,
        )


search = _search
search_async = _search_async
search_sync = _search_sync
adapter = CascadenceAdapter()
