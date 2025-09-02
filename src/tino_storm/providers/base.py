from __future__ import annotations

import asyncio
import importlib
import logging
import os
import atexit
import threading
from abc import ABC, abstractmethod
from typing import Iterable, List, Dict, Any, Optional, Coroutine

from ..search_result import ResearchResult, as_research_result

from ..ingest import search_vaults
from ..core.rm import BingSearch
from ..events import ResearchAdded, event_emitter


_loop: Optional[asyncio.AbstractEventLoop] = None
_thread: Optional[threading.Thread] = None
_loop_lock = threading.Lock()


def _start_loop() -> asyncio.AbstractEventLoop:
    """Start a background event loop and return it."""

    global _loop, _thread
    with _loop_lock:
        if _loop is not None:
            return _loop

        _loop = asyncio.new_event_loop()

        def run() -> None:
            asyncio.set_event_loop(_loop)
            _loop.run_forever()

        _thread = threading.Thread(target=run, name="tino-storm-loop", daemon=True)
        _thread.start()
        atexit.register(_stop_loop)
        return _loop


def _get_loop() -> Optional[asyncio.AbstractEventLoop]:
    return _loop


def _get_loop_thread() -> Optional[threading.Thread]:
    return _thread


def _stop_loop() -> None:
    """Stop the background event loop."""

    global _loop, _thread
    loop, thread = _loop, _thread
    _loop = None
    _thread = None
    if loop is not None:
        loop.call_soon_threadsafe(loop.stop)
        if thread is not None:
            thread.join()
        loop.close()


def format_bing_items(items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize raw Bing results into the internal search format."""

    formatted: List[Dict[str, Any]] = []
    for item in items:
        url = item.get("url")
        if not url:
            continue
        snippets = item.get("snippets") or [item.get("description", "")]
        formatted.append(
            {"url": url, "snippets": snippets, "meta": {"title": item.get("title")}}
        )
    return formatted


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
        # Cache summarization tasks by snippet text
        self._summary_tasks: Dict[str, asyncio.Task] = {}

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
        self, snippets: List[str], *, max_chars: int = 200
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
                    result = await asyncio.to_thread(summarizer, prompt)
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
        task.add_done_callback(lambda t, k=key: self._summary_tasks.pop(k, None))
        return await task

    def _run(self, coro: Coroutine[Any, Any, Any]) -> Any:
        """Run *coro* on the background event loop."""

        loop = _get_loop()
        if loop is None:
            loop = _start_loop()
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result()

    def _summarize(self, snippets: List[str], *, max_chars: int = 200) -> Optional[str]:
        """Synchronous wrapper for ``_summarize_async``."""

        return self._run(self._summarize_async(snippets, max_chars=max_chars))

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
        )
        if raw_results:
            results = [as_research_result(r) for r in raw_results]
        else:
            web = self._bing_search(query)
            formatted = format_bing_items(web)
            results = [as_research_result(r) for r in formatted]

        unsummarized = [res for res in results if not getattr(res, "summary", None)]
        if unsummarized:

            async def _gather():
                return await asyncio.gather(
                    *(self._summarize_async(res.snippets) for res in unsummarized)
                )

            summaries = self._run(_gather())
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
        )
        if raw_results:
            results = [as_research_result(r) for r in raw_results]
        else:
            web = await asyncio.to_thread(self._bing_search, query)
            formatted = format_bing_items(web)
            results = [as_research_result(r) for r in formatted]

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
