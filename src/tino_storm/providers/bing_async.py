from __future__ import annotations

import os
from typing import Iterable, List, Optional

import httpx

from .base import Provider, format_bing_items
from .registry import register_provider
from ..search_result import ResearchResult, as_research_result

BING_ENDPOINT = "https://api.bing.microsoft.com/v7.0/search"


@register_provider("bing_async")
class BingAsyncProvider(Provider):
    """Asynchronous Bing search provider using httpx."""

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
        api_key = os.environ.get("BING_SEARCH_API_KEY")
        if not api_key:
            return []
        headers = {"Ocp-Apim-Subscription-Key": api_key}
        params = {"q": query, "count": k_per_vault}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(BING_ENDPOINT, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        items = data.get("webPages", {}).get("value", [])
        # Map Bing's ``snippet`` field to ``description`` expected by
        # ``format_bing_items`` for snippet normalization.
        normalized = []
        for item in items:
            if "snippet" in item and "description" not in item and "snippets" not in item:
                item = {**item, "description": item["snippet"]}
            if "name" in item and "title" not in item:
                item = {**item, "title": item["name"]}
            normalized.append(item)
        formatted = format_bing_items(normalized)
        return [as_research_result(r) for r in formatted]

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
        raise NotImplementedError("BingAsyncProvider only implements search_async")
