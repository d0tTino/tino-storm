"""Utilities for advanced retrieval ranking."""

from .rrf import reciprocal_rank_fusion
from typing import List, Dict, Any


def combine_ranks(
    recency_ranking: List[Dict[str, Any]],
    authority_ranking: List[Dict[str, Any]],
    similarity_ranking: List[Dict[str, Any]],
    k: int = 60,
) -> List[Dict[str, Any]]:
    """Fuse results from three ranking strategies using RRF."""
    return reciprocal_rank_fusion(
        [recency_ranking, authority_ranking, similarity_ranking], k=k
    )


__all__ = ["reciprocal_rank_fusion", "combine_ranks"]
