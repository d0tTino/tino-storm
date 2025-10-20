from __future__ import annotations

import asyncio
import importlib
import logging
import os
import threading
from abc import ABC, abstractmethod
from collections import OrderedDict
from contextlib import suppress
from typing import Any, Awaitable, Dict, Iterable, List, Optional, TypeVar

from ..search_result import ResearchResult, as_research_result

from ..ingest import search_vaults
from ..core.rm import BingSearch
from ..events import ResearchAdded, event_emitter

# Maximum number of in-flight or cached summary tasks.
SUMMARY_CACHE_LIMIT = 100

T = TypeVar("T")


def _run_coroutine_in_loop(coro: Awaitable[T]) -> T:
    loop = asyncio.new_event_loop()
    try:
        try:
            result = loop.run_until_complete(coro)
        finally:
            with suppress(Exception):
                loop.run_until_complete(loop.shutdown_asyncgens())
        return result
    finally:
        loop.close()


def _run_coroutine_in_new_loop(coro: Awaitable[T]) -> T:
    """Execute *coro* even when the caller already has a running loop."""

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return _run_coroutine_in_loop(coro)

    result: list[T] = []
    error: list[BaseException] = []

    def runner() -> None:
        try:
            result.append(_run_coroutine_in_loop(coro))
        except BaseException as exc:  # pragma: no cover - propagated below
            error.append(exc)

    thread = threading.Thread(target=runner, name="storm-loop-runner")
    thread.start()
    thread.join()

    if error:
        raise error[0]
    return result[0]


def format_bing_items(items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize raw Bing results into the internal search format."""

    formatted: List[Dict[str, Any]] = []
    for item in items:
        url = item.get("url")
        if not url:
            continue
        snippets = item.get("snippets") or [item.get("description", "")]
        meta: Dict[str, Any] = {"source": "bing"}
        if "title" in item:
            meta["title"] = item.get("title")
        formatted.append({"url": url, "snippets": snippets, "meta": meta})
    return formatted


def _ensure_source(results: Iterable[ResearchResult], source: str) -> None:
    """Attach a ``source`` hint to each result when missing."""

    for result in results:
        meta = dict(result.meta) if result.meta else {}
        meta.setdefault("source", source)
        result.meta = meta


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
        timeout: Optional[float] = None,
    ) -> List[ResearchResult]:
        """Asynchronously search and return results."""
        return await asyncio.to_thread(
            self.search_sync,
            query,
            vaults,
            k_per_vault=k_per_vault,
            rrf_k=rrf_k,
            chroma_path=chroma_path,
            vault=vault,
            timeout=timeout,
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
        timeout: Optional[float] = None,
    ) -> List[ResearchResult]:
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
        self._summarizer = None
        # Cache summarization tasks by snippet text, keeping insertion order
        self._summary_tasks: OrderedDict[str, asyncio.Task] = OrderedDict()

    def _bing_search(
        self, query: str, *, timeout: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        if self._bing is None:
            api_key = os.environ.get("BING_SEARCH_API_KEY")
            if not api_key:
                return []
            self._bing = BingSearch(
                bing_search_api_key=api_key, k=self.bing_k, **self.bing_kwargs
            )
        try:
            kwargs: Dict[str, Any] = {}
            if timeout is not None:
                kwargs["timeout"] = timeout
            return self._bing(query, **kwargs)
        except Exception as e:  # pragma: no cover - network issues
            logging.error(f"Bing search failed for query {query}: {e}")
            event_emitter.emit_sync(
                ResearchAdded(topic=query, information_table={"error": str(e)})
            )
            return []

    def _get_summarizer(self):
        """Lazily construct an LLM summarizer if configured.

        The summarizer is only enabled when the ``STORM_SUMMARY_MODEL``
        environment variable is set. This keeps heavy LLM dependencies
        optional for users that do not need summarization.
        """

        model_name = os.environ.get("STORM_SUMMARY_MODEL")
        if not model_name:
            return None

        if self._summarizer is None:
            try:  # pragma: no cover - exercised when env var is set
                from ..lm import LitellmModel

                self._summarizer = LitellmModel(model=model_name, max_tokens=60)
            except Exception as e:  # pragma: no cover - missing optional deps
                logging.error(f"Failed to initialize summarizer: {e}")
                self._summarizer = False

        return self._summarizer or None

    async def _summarize_async(
        self,
        snippets: List[str],
        *,
        max_chars: int = 200,
        timeout: Optional[float] = None,
    ) -> Optional[str]:
        """Return a short summary for the provided snippets asynchronously."""

        if not snippets:
            return None

        key = "\n".join(snippets)
        cached = self._summary_tasks.get(key)
        if cached is not None:
            return await cached

        async def _run() -> str:
            summarizer = self._get_summarizer()
            summary: Optional[str] = None
            if summarizer:
                try:  # pragma: no cover - exercised when env var is set
                    prompt = (
                        "Summarize the following in one short sentence:\n" + snippets[0]
                    )
                    if timeout is None:
                        t_str = os.environ.get("STORM_SUMMARY_TIMEOUT")
                        timeout_val = float(t_str) if t_str else None
                    else:
                        timeout_val = timeout
                    result = await asyncio.wait_for(
                        asyncio.to_thread(summarizer, prompt), timeout=timeout_val
                    )
                    summary = result[0].strip()
                except Exception as e:  # pragma: no cover - network/LLM issues
                    logging.error(f"LLM summarization failed: {e}")
                    event_emitter.emit_sync(
                        ResearchAdded(
                            topic=snippets[0],
                            information_table={"error": str(e)},
                        )
                    )

            if summary is None:
                summary = snippets[0]

            return summary[:max_chars]

        task: asyncio.Task = asyncio.create_task(_run())
        self._summary_tasks[key] = task
        while len(self._summary_tasks) > SUMMARY_CACHE_LIMIT:
            self._summary_tasks.popitem(last=False)
        task.add_done_callback(lambda t, k=key: self._summary_tasks.pop(k, None))
        return await task

    def _summarize(
        self,
        snippets: List[str],
        *,
        max_chars: int = 200,
        timeout: Optional[float] = None,
    ) -> Optional[str | asyncio.Task]:
        """Run ``_summarize_async`` using the current event loop if present.

        When called without a running event loop, the coroutine is executed on
        a dedicated loop and the summary string is returned. If an event loop
        is already running, a task is created and returned to allow the caller
        to await the result without blocking.
        """

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return _run_coroutine_in_new_loop(
                self._summarize_async(snippets, max_chars=max_chars, timeout=timeout)
            )
        return loop.create_task(
            self._summarize_async(snippets, max_chars=max_chars, timeout=timeout)
        )

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
        raw_results = search_vaults(
            query,
            vaults,
            k_per_vault=k_per_vault,
            rrf_k=rrf_k,
            chroma_path=chroma_path,
            vault=vault,
            timeout=timeout,
        )
        if raw_results:
            results = [as_research_result(r) for r in raw_results]
            _ensure_source(results, "vault")
        else:
            web = self._bing_search(query, timeout=timeout)
            formatted = format_bing_items(web)
            results = [as_research_result(r) for r in formatted]
            _ensure_source(results, "bing")

        unsummarized = [res for res in results if not getattr(res, "summary", None)]
        if unsummarized:

            async def _gather():
                return await asyncio.gather(
                    *(self._summarize_async(res.snippets) for res in unsummarized)
                )

            summaries = _run_coroutine_in_new_loop(_gather())
            for res, summary in zip(unsummarized, summaries):
                res.summary = summary

        return results

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
        raw_results = await asyncio.to_thread(
            search_vaults,
            query,
            vaults,
            k_per_vault=k_per_vault,
            rrf_k=rrf_k,
            chroma_path=chroma_path,
            vault=vault,
            timeout=timeout,
        )
        if raw_results:
            results = [as_research_result(r) for r in raw_results]
            _ensure_source(results, "vault")
        else:
            web = await asyncio.to_thread(self._bing_search, query, timeout=timeout)
            formatted = format_bing_items(web)
            results = [as_research_result(r) for r in formatted]
            _ensure_source(results, "bing")

        unsummarized = [res for res in results if not getattr(res, "summary", None)]
        if unsummarized:
            summaries = await asyncio.gather(
                *(self._summarize_async(res.snippets) for res in unsummarized)
            )
            for res, summary in zip(unsummarized, summaries):
                res.summary = summary

        return results


def load_provider(spec: str) -> Provider:
    module_name, obj = spec.rsplit(".", 1)
    mod = importlib.import_module(module_name)
    cls = getattr(mod, obj)
    if not isinstance(cls, type) or not issubclass(cls, Provider):
        raise TypeError(f"{spec} is not a Provider subclass")

    return cls()
