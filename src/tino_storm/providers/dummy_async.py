from __future__ import annotations

from typing import Iterable, List, Optional

from .base import Provider
from ..search_result import ResearchResult


class DummyAsyncProvider(Provider):
    """Provider with an asynchronous search method for testing."""

    async def search_async(
        self,
        query: str,
        vaults: Iterable[str],
        *,
        k_per_vault: int = 5,
        rrf_k: int = 60,
        chroma_path: Optional[str] = None,
        vault: Optional[str] = None,
    ) -> List[ResearchResult]:
        return [
            ResearchResult(url="", snippets=[], meta={"query": query, "vaults": list(vaults)})
        ]

    def search_sync(
        self,
        query: str,
        vaults: Iterable[str],
        *,
        k_per_vault: int = 5,
        rrf_k: int = 60,
        chroma_path: Optional[str] = None,
        vault: Optional[str] = None,
    ) -> List[ResearchResult]:
        raise NotImplementedError("DummyAsyncProvider only implements search_async")
