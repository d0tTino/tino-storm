import asyncio
import logging
import os
from typing import Iterable, List, Optional

from .providers import (
    DefaultProvider,
    load_provider,
    Provider,
    provider_registry,
    ProviderAggregator,
)
from .events import ResearchAdded, event_emitter
from .search_result import ResearchResult
from .ingest.utils import list_vaults


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
                return load_provider(spec)
            except Exception as e:
                logging.exception("Failed to load provider '%s'", spec)
                _emit_load_error(spec, e)
                raise ResearchError(
                    f"Failed to load provider '{spec}': {e}", provider_spec=spec
                ) from e
        return DefaultProvider()
    if isinstance(provider, str):
        if "," in provider:
            specs = [p.strip() for p in provider.split(",") if p.strip()]
            return ProviderAggregator(specs)
        try:
            return provider_registry.get(provider)
        except KeyError:
            try:
                return load_provider(provider)
            except Exception as e:
                logging.exception("Failed to load provider '%s'", provider)
                _emit_load_error(provider, e)
                raise ResearchError(
                    f"Failed to load provider '{provider}': {e}",
                    provider_spec=provider,
                ) from e
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


def search(
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
    """Query ``vaults`` synchronously or return an awaitable when in an event loop."""

    if vaults is None:
        vaults = list_vaults()

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        provider = _resolve_provider(provider)
        try:
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
        except Exception as e:
            logging.error(f"Search failed for query {query}: {e}")
            event_emitter.emit_sync(
                ResearchAdded(topic=query, information_table={"error": str(e)})
            )
            raise ResearchError(str(e)) from e

    return search_async(
        query,
        vaults,
        k_per_vault=k_per_vault,
        rrf_k=rrf_k,
        chroma_path=chroma_path,
        vault=vault,
        provider=provider,
        timeout=timeout,
    )
