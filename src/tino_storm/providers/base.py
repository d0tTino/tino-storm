from __future__ import annotations

import asyncio
import importlib
import logging
import os
from abc import ABC, abstractmethod
from typing import Iterable, List, Dict, Any, Optional

from ..ingest import search_vaults
from ..core.rm import BingSearch
from ..events import ResearchAdded, event_emitter


class Provider(ABC):
    """Base interface for search providers."""

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
        """Asynchronously search and return results."""
        return await asyncio.to_thread(
            self.search_sync,
            query,
            vaults,
            k_per_vault=k_per_vault,
            rrf_k=rrf_k,
            chroma_path=chroma_path,
            vault=vault,
        )

    @abstractmethod
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
        """Synchronously search and return results."""

    def search(self, *args, **kwargs):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return self.search_sync(*args, **kwargs)
        return self.search_async(*args, **kwargs)


class DefaultProvider(Provider):
    """Default provider using local vaults and optional Bing search."""

    def __init__(self, bing_k: int = 5, **bing_kwargs):
        self.bing_k = bing_k
        self.bing_kwargs = bing_kwargs
        self._bing = None

    def _bing_search(self, query: str) -> List[Dict[str, Any]]:
        if self._bing is None:
            api_key = os.environ.get("BING_SEARCH_API_KEY")
            if not api_key:
                return []
            self._bing = BingSearch(
                bing_search_api_key=api_key, k=self.bing_k, **self.bing_kwargs
            )
        try:
            return self._bing(query)
        except Exception as e:  # pragma: no cover - network issues
            logging.error(f"Bing search failed for query {query}: {e}")
            event_emitter.emit(
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
    ) -> List[Dict[str, Any]]:
        results = search_vaults(
            query,
            vaults,
            k_per_vault=k_per_vault,
            rrf_k=rrf_k,
            chroma_path=chroma_path,
            vault=vault,
        )
        if results:
            return results
        web = self._bing_search(query)
        formatted = []
        for item in web:
            formatted.append(
                {
                    "url": item.get("url"),
                    "snippets": item.get("snippets") or [item.get("description", "")],
                    "meta": {"title": item.get("title")},
                }
            )
        return formatted


def load_provider(spec: str) -> Provider:
    module_name, obj = spec.rsplit(".", 1)
    mod = importlib.import_module(module_name)
    cls = getattr(mod, obj)
    if not isinstance(cls, type) or not issubclass(cls, Provider):
        raise TypeError(f"{spec} is not a Provider subclass")

    return cls()
