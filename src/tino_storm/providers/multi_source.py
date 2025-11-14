from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Iterable, List, Optional, Set

from .aggregator import canonical_url, _update_best_metadata
from .base import DefaultProvider, _run_coroutine_in_new_loop, format_bing_items
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
        canonical_to_result: Dict[str, ResearchResult] = {}

        def add_ranked_results(results: Iterable[ResearchResult]) -> None:
            ranking: List[Dict[str, Any]] = []
            seen: Set[str] = set()

            for result in results:
                if not result.url:
                    continue

                key = canonical_url(result.url)
                existing = canonical_to_result.get(key)
                if existing is None:
                    canonical_to_result[key] = result
                else:
                    _update_best_metadata(existing, result)

                if key not in seen:
                    ranking.append({"url": key})
                    seen.add(key)

            if ranking:
                rankings.append(ranking)

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
                annotated_vault: List[ResearchResult] = []
                for item in res:
                    entry = dict(item)
                    meta = dict(entry.get("meta") or {})
                    meta.setdefault("source", "vault")
                    _ensure_provenance(meta, "vault")
                    entry["meta"] = meta
                    annotated_vault.append(as_research_result(entry))
                add_ranked_results(annotated_vault)
            elif source == "docs" and res:
                docs_results: List[ResearchResult] = []
                for r in res:
                    meta = dict(r.meta) if r.meta else {}
                    meta.setdefault("source", "docs_hub")
                    _ensure_provenance(meta, "docs_hub")
                    docs_results.append(
                        ResearchResult(
                            url=r.url,
                            snippets=list(r.snippets),
                            meta=meta,
                            summary=r.summary,
                            score=r.score,
                            posterior=r.posterior,
                        )
                    )

                add_ranked_results(docs_results)
            elif source == "bing":
                formatted = format_bing_items(res)
                for item in formatted:
                    meta = dict(item.get("meta") or {})
                    meta.setdefault("source", "bing")
                    _ensure_provenance(meta, "bing")
                    item["meta"] = meta
                if formatted:
                    scored = score_results(formatted)
                    bing_results = [as_research_result(item) for item in scored]
                    add_ranked_results(bing_results)

        if not canonical_to_result:
            return []

        ordered_keys: List[str]
        if rankings:
            fused = reciprocal_rank_fusion(rankings, k=rrf_k)
            ordered_keys = [
                entry["url"]
                for entry in fused
                if entry.get("url") in canonical_to_result
            ]
        else:
            ordered_keys = list(canonical_to_result.keys())

        seen: Set[str] = set()
        ordered_results: List[ResearchResult] = []
        for key in ordered_keys:
            if key in seen:
                continue
            seen.add(key)
            ordered_results.append(canonical_to_result[key])

        for key, result in canonical_to_result.items():
            if key not in seen:
                ordered_results.append(result)

        serialized = [
            {
                "url": result.url,
                "snippets": result.snippets,
                "meta": result.meta,
                "summary": result.summary,
                "score": result.score,
                "posterior": result.posterior,
            }
            for result in ordered_results
        ]

        scored = add_posteriors(serialized)
        for result, scored_data in zip(ordered_results, scored):
            posterior = scored_data.get("posterior")
            if posterior is None:
                continue
            if result.posterior is None:
                result.posterior = posterior
            else:
                result.posterior = max(result.posterior, posterior)

        return ordered_results

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
