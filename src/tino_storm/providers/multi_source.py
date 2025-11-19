from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Iterable, List, Optional

from .aggregator import _fuse_results
from .base import DefaultProvider, _run_coroutine_in_new_loop, format_bing_items
from .docs_hub import DocsHubProvider
from .registry import register_provider
from ..events import ResearchAdded, event_emitter
from ..ingest import search_vaults
from ..retrieval import add_posteriors, score_results
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

        provider_results: List[List[ResearchResult]] = []

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
                if annotated_vault:
                    provider_results.append(annotated_vault)
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

                if docs_results:
                    provider_results.append(docs_results)
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
                    if bing_results:
                        provider_results.append(bing_results)

        limit = min(k_per_vault, rrf_k) if k_per_vault is not None else rrf_k
        ordered_results = _fuse_results(provider_results, limit=limit, rrf_k=rrf_k)

        if not ordered_results:
            return []

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
