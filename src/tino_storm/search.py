import asyncio
from typing import Iterable, List, Dict, Any, Optional

import os

from .providers import DefaultProvider, load_provider, Provider


def _resolve_provider(provider: Provider | str | None) -> Provider:
    if provider is None:
        spec = os.environ.get("STORM_SEARCH_PROVIDER")
        if spec:
            return load_provider(spec)
        return DefaultProvider()
    if isinstance(provider, str):
        return load_provider(provider)
    return provider


async def search_async(
    query: str,
    vaults: Iterable[str],
    *,
    k_per_vault: int = 5,
    rrf_k: int = 60,
    chroma_path: Optional[str] = None,
    vault: Optional[str] = None,
    provider: Provider | str | None = None,
) -> List[Dict[str, Any]]:
    """Asynchronously query ``vaults`` using the configured provider."""

    provider = _resolve_provider(provider)
    return await provider.search_async(
        query,
        vaults,
        k_per_vault=k_per_vault,
        rrf_k=rrf_k,
        chroma_path=chroma_path,
        vault=vault,
    )


def search(
    query: str,
    vaults: Iterable[str],
    *,
    k_per_vault: int = 5,
    rrf_k: int = 60,
    chroma_path: Optional[str] = None,
    vault: Optional[str] = None,
    provider: Provider | str | None = None,
):
    """Query ``vaults`` synchronously or return an awaitable when in an event loop."""

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        provider = _resolve_provider(provider)
        return provider.search_sync(
            query,
            vaults,
            k_per_vault=k_per_vault,
            rrf_k=rrf_k,
            chroma_path=chroma_path,
            vault=vault,
        )

    return search_async(
        query,
        vaults,
        k_per_vault=k_per_vault,
        rrf_k=rrf_k,
        chroma_path=chroma_path,
        vault=vault,
        provider=provider,
    )
