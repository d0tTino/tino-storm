from __future__ import annotations

from typing import Iterable, List, Optional

from .base import Provider
from .registry import register_provider
from ..search_result import ResearchResult, as_research_result
from ..ingest import search_vaults


@register_provider("docs_hub")
class DocsHubProvider(Provider):
    """Provider that queries the local Docs/knowledge index."""

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
        """Synchronously search the local docs index."""
        raw_results = search_vaults(
            query,
            vaults,
            k_per_vault=k_per_vault,
            rrf_k=rrf_k,
            chroma_path=chroma_path,
            vault=vault,
        )
        return [as_research_result(r) for r in raw_results]
