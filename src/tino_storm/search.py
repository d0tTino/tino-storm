import asyncio
from typing import Iterable, List, Dict, Any, Optional
from pathlib import Path

import os
import logging

from .providers import (
    DefaultProvider,
    load_provider,
    Provider,
    provider_registry,
    ProviderAggregator,
)
from .events import ResearchAdded, event_emitter


class ResearchError(RuntimeError):
    """Raised when a search provider fails to complete the query."""


def _resolve_provider(provider: Provider | str | None) -> Provider:
    if provider is None:
        spec = os.environ.get("STORM_SEARCH_PROVIDER")
        if spec:
            return load_provider(spec)
        return DefaultProvider()
    if isinstance(provider, str):
        if "," in provider:
            specs = [p.strip() for p in provider.split(",") if p.strip()]
            return ProviderAggregator(specs)
        try:
            return provider_registry.get(provider)
        except KeyError:
            return load_provider(provider)
    return provider


def list_vaults() -> List[str]:
    """Return available vault names from the local Chroma storage."""

    chroma_root = Path(
        os.environ.get("STORM_CHROMA_PATH", Path.home() / ".tino_storm" / "chroma")
    ).expanduser()
    if not chroma_root.exists():
        return []
    return [p.name for p in chroma_root.iterdir() if p.is_dir()]


async def search_async(
    query: str,
    vaults: Iterable[str] | None = None,
    *,
    k_per_vault: int = 5,
    rrf_k: int = 60,
    chroma_path: Optional[str] = None,
    vault: Optional[str] = None,
    provider: Provider | str | None = None,
) -> List[Dict[str, Any]]:
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
        )
    except Exception as e:
        logging.error(f"Search failed for query {query}: {e}")

        event_emitter.emit(
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
):
    """Query ``vaults`` synchronously or return an awaitable when in an event loop."""

    if vaults is None:
        vaults = list_vaults()

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        provider = _resolve_provider(provider)
        try:
            return provider.search_sync(
                query,
                vaults,
                k_per_vault=k_per_vault,
                rrf_k=rrf_k,
                chroma_path=chroma_path,
                vault=vault,
            )
        except Exception as e:
            logging.error(f"Search failed for query {query}: {e}")

            event_emitter.emit(
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
    )
