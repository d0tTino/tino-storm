import asyncio
import logging
import os
import threading
from typing import Callable, Iterable, List, Optional

from .providers import (
    DefaultProvider,
    load_provider,
    Provider,
    provider_registry,
    ProviderAggregator,
    get_docs_hub_provider,
    get_vector_db_provider,
)
from .events import ResearchAdded, event_emitter
from .search_result import ResearchResult
from .ingest.utils import list_vaults


_PROVIDER_CACHE: dict[str, Provider] = {}
_PROVIDER_CACHE_LOCK = threading.Lock()
_DEFAULT_PROVIDER_CACHE_KEY = "__default__"


def _split_provider_specs(spec: str) -> List[str]:
    return [part.strip() for part in spec.split(",") if part.strip()]


def _get_or_create_provider(key: str, factory: Callable[[], Provider]) -> Provider:
    with _PROVIDER_CACHE_LOCK:
        provider_instance = _PROVIDER_CACHE.get(key)
        if provider_instance is None:
            provider_instance = factory()
            _PROVIDER_CACHE[key] = provider_instance
        return provider_instance


class ResearchError(RuntimeError):
    """Raised when a search provider fails to complete the query."""

    def __init__(self, message: str, *, provider_spec: str | None = None) -> None:
        super().__init__(message)
        self.provider_spec = provider_spec


def _resolve_provider(provider: Provider | str | None) -> Provider:
    def _emit_load_error(spec: str, err: Exception) -> None:
        event = ResearchAdded(topic=spec, information_table={"error": str(err)})
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            event_emitter.emit_sync(event)
        else:
            loop.create_task(event_emitter.emit(event))

    if provider is None:
        spec = os.environ.get("STORM_SEARCH_PROVIDER")
        if spec:
            try:
                if "," in spec:
                    specs = _split_provider_specs(spec)

                    def factory() -> Provider:
                        return ProviderAggregator(specs)

                    return _get_or_create_provider(spec, factory)

                return _get_or_create_provider(spec, lambda: load_provider(spec))
            except Exception as e:
                logging.exception("Failed to load provider '%s'", spec)
                _emit_load_error(spec, e)
                raise ResearchError(str(e), provider_spec=spec) from e
        default_provider = _get_or_create_provider(
            _DEFAULT_PROVIDER_CACHE_KEY, DefaultProvider
        )

        extras: List[Provider] = []

        docs_hub_provider = get_docs_hub_provider()
        if docs_hub_provider is not None:
            extras.append(docs_hub_provider)

        vector_provider = get_vector_db_provider()
        if vector_provider is not None and vector_provider not in extras:
            extras.append(vector_provider)

        if extras:
            extra_names = [
                getattr(p, "name", None) or p.__class__.__name__ for p in extras
            ]
            cache_key = "__aggregated__:" + ",".join(extra_names)

            def factory() -> Provider:
                return ProviderAggregator([default_provider, *extras])

            return _get_or_create_provider(cache_key, factory)

        return default_provider
    if isinstance(provider, str):
        if "," in provider:
            specs = _split_provider_specs(provider)
            return ProviderAggregator(specs)
        try:
            return provider_registry.get(provider)
        except KeyError:
            try:
                with _PROVIDER_CACHE_LOCK:
                    provider_instance = _PROVIDER_CACHE.get(provider)
                    if provider_instance is None:
                        provider_instance = load_provider(provider)
                        _PROVIDER_CACHE[provider] = provider_instance
                    return provider_instance
            except Exception as e:
                logging.exception("Failed to load provider '%s'", provider)
                _emit_load_error(provider, e)
                raise ResearchError(str(e), provider_spec=provider) from e
    return provider


async def search_async(
    query: str,
    vaults: Iterable[str] | None = None,
    *,
    k_per_vault: int = 5,
    rrf_k: int = 60,
    chroma_path: Optional[str] = None,
    vault: Optional[str] = None,
    provider: Provider | str | None = None,
    timeout: Optional[float] = None,
) -> List[ResearchResult]:
    """Asynchronously query ``vaults`` using the configured provider."""

    if vaults is None:
        vaults = list_vaults()

    provider = _resolve_provider(provider)
    try:
        return await provider.search_async(
            query,
            vaults,
            k_per_vault=k_per_vault,
            rrf_k=rrf_k,
            chroma_path=chroma_path,
            vault=vault,
            timeout=timeout,
        )
    except Exception as e:
        logging.error(f"Search failed for query {query}: {e}")
        await event_emitter.emit(
            ResearchAdded(topic=query, information_table={"error": str(e)})
        )
        raise ResearchError(str(e)) from e


def search_sync(
    query: str,
    vaults: Iterable[str] | None = None,
    *,
    k_per_vault: int = 5,
    rrf_k: int = 60,
    chroma_path: Optional[str] = None,
    vault: Optional[str] = None,
    provider: Provider | str | None = None,
    timeout: Optional[float] = None,
) -> List[ResearchResult]:
    """Synchronously query ``vaults`` using the configured provider."""

    if vaults is None:
        vaults = list_vaults()

    provider = _resolve_provider(provider)

    try:
        return provider.search_sync(
            query,
            vaults,
            k_per_vault=k_per_vault,
            rrf_k=rrf_k,
            chroma_path=chroma_path,
            vault=vault,
            timeout=timeout,
        )
    except NotImplementedError:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            try:
                return asyncio.run(
                    provider.search_async(
                        query,
                        vaults,
                        k_per_vault=k_per_vault,
                        rrf_k=rrf_k,
                        chroma_path=chroma_path,
                        vault=vault,
                        timeout=timeout,
                    )
                )
            except Exception as e:  # pragma: no cover - defensive fallback
                logging.error(f"Search failed for query {query}: {e}")
                event_emitter.emit_sync(
                    ResearchAdded(topic=query, information_table={"error": str(e)})
                )
                raise ResearchError(str(e)) from e
        raise RuntimeError(
            "search_sync cannot run inside a running event loop when the provider "
            "only implements asynchronous search; use search_async instead."
        ) from None
    except Exception as e:
        logging.error(f"Search failed for query {query}: {e}")
        event_emitter.emit_sync(
            ResearchAdded(topic=query, information_table={"error": str(e)})
        )
        raise ResearchError(str(e)) from e


async def search(
    query: str,
    vaults: Iterable[str] | None = None,
    *,
    k_per_vault: int = 5,
    rrf_k: int = 60,
    chroma_path: Optional[str] = None,
    vault: Optional[str] = None,
    provider: Provider | str | None = None,
    timeout: Optional[float] = None,
) -> List[ResearchResult]:
    """Asynchronously query ``vaults`` via :func:`search_async`."""

    return await search_async(
        query,
        vaults,
        k_per_vault=k_per_vault,
        rrf_k=rrf_k,
        chroma_path=chroma_path,
        vault=vault,
        provider=provider,
        timeout=timeout,
    )
