import asyncio
from typing import Iterable, List, Dict, Any, Optional

from .ingest import search_vaults


async def search_async(
    query: str,
    vaults: Iterable[str],
    *,
    k_per_vault: int = 5,
    rrf_k: int = 60,
    chroma_path: Optional[str] = None,
    vault: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Asynchronously query ``vaults`` using :func:`search_vaults` in a thread."""

    return await asyncio.to_thread(
        search_vaults,
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
):
    """Query ``vaults`` synchronously or return an awaitable when in an event loop."""

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return search_vaults(
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
    )
