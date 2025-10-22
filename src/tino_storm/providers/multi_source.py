from __future__ import annotations

import asyncio
import logging
from typing import Iterable, List, Dict, Any, Optional

from .aggregator import canonical_url, _update_best_metadata
from .base import DefaultProvider, format_bing_items, _run_coroutine_in_new_loop
from .docs_hub import DocsHubProvider
from .registry import register_provider
from ..events import ResearchAdded, event_emitter
from ..ingest import search_vaults
from ..retrieval import reciprocal_rank_fusion, score_results, add_posteriors
from ..search_result import ResearchResult, as_research_result


def _ensure_provenance(meta: Dict[str, Any], provider_id: str) -> Dict[str, Any]:
    """Return ``meta`` annotated with the given ``provider_id`` provenance."""

    existing = meta.get("providers")
    if not existing:
        providers: List[str] = []
    elif isinstance(existing, list):
        providers = [str(p) for p in existing if p]
    else:
        providers = [str(existing)]

    if provider_id not in providers:
        providers.append(provider_id)

    meta["providers"] = providers
    return meta


@register_provider("multi_source")
class MultiSourceProvider(DefaultProvider):
    """Provider that queries local vaults, DocsHub, and Bing in parallel."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.docs_provider = DocsHubProvider()

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
        tasks = []
        task_names: List[str] = []

        docs_will_handle_local = not self.docs_provider.is_remote_configured

        if not docs_will_handle_local:
            vault_task = asyncio.to_thread(
                search_vaults,
                query,
                vaults,
                k_per_vault=k_per_vault,
                rrf_k=rrf_k,
                chroma_path=chroma_path,
                vault=vault,
                timeout=timeout,
            )
            tasks.append(vault_task)
            task_names.append("vault")

        docs_task = self.docs_provider.search_async(
            query,
            vaults,
            k_per_vault=k_per_vault,
            rrf_k=rrf_k,
            chroma_path=chroma_path,
            vault=vault,
            timeout=timeout,
        )
        bing_task = asyncio.to_thread(self._bing_search, query, timeout=timeout)
        tasks.append(docs_task)
        task_names.append("docs")

        tasks.append(bing_task)
        task_names.append("bing")

        gathered_results = await asyncio.gather(*tasks, return_exceptions=True)
        results_map = dict(zip(task_names, gathered_results))

        vault_res = results_map.get("vault") if "vault" in results_map else None
        docs_res = results_map.get("docs")
        bing_res = results_map.get("bing")

        docs_used_local = (
            not isinstance(docs_res, Exception)
            and bool(docs_res)
            and all(
                getattr(r, "meta", {}).get("docs_hub_origin") == "local" for r in docs_res
            )
        )

        if docs_used_local:
            vault_res = None

        rankings: List[List[Dict[str, Any]]] = []

        for source, res in (
            ("vault", vault_res),
            ("docs", docs_res),
            ("bing", bing_res),
        ):
            if res is None:
                continue
            if isinstance(res, Exception):
                logging.exception("%s search failed in MultiSourceProvider", source)
                await event_emitter.emit(
                    ResearchAdded(topic=query, information_table={"error": str(res)})
                )
                res = []

            if source == "vault" and res:
                annotated_vault: List[Dict[str, Any]] = []
                for item in res:
                    entry = dict(item)
                    meta = dict(entry.get("meta") or {})
                    meta.setdefault("source", "vault")
                    _ensure_provenance(meta, "vault")
                    entry["meta"] = meta
                    annotated_vault.append(entry)
                rankings.append(annotated_vault)
            elif source == "docs" and res:
                formatted_docs: List[Dict[str, Any]] = []
                for r in res:
                    info: Dict[str, Any] = {
                        "url": r.url,
                        "snippets": r.snippets,
                        "meta": dict(r.meta),
                    }
                    info["meta"].setdefault("source", "docs_hub")
                    _ensure_provenance(info["meta"], "docs_hub")
                    if r.summary is not None:
                        info["summary"] = r.summary
                    if r.score is not None:
                        info["score"] = r.score
                    if r.posterior is not None:
                        info["posterior"] = r.posterior
                    formatted_docs.append(info)

                rankings.append(formatted_docs)
            elif source == "bing":
                formatted = format_bing_items(res)
                for item in formatted:
                    meta = dict(item.get("meta") or {})
                    _ensure_provenance(meta, "bing")
                    item["meta"] = meta
                if formatted:
                    rankings.append(score_results(formatted))

        if not rankings:
            return []

        fused = reciprocal_rank_fusion(rankings, k=rrf_k)
        scored = add_posteriors(fused)
        results = [as_research_result(r) for r in scored]

        deduped: Dict[str, ResearchResult] = {}
        order: List[str] = []
        for result in results:
            key = canonical_url(result.url) if result.url else result.url
            if key not in deduped:
                deduped[key] = result
                order.append(key)
            else:
                _update_best_metadata(deduped[key], result)

        return [deduped[key] for key in order]

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
        coroutine = self.search_async(
            query,
            vaults,
            k_per_vault=k_per_vault,
            rrf_k=rrf_k,
            chroma_path=chroma_path,
            vault=vault,
            timeout=timeout,
        )

        return _run_coroutine_in_new_loop(coroutine)
