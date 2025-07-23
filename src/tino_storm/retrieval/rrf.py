from collections import defaultdict
from typing import List, Dict, Any


def reciprocal_rank_fusion(
    rankings: List[List[Dict[str, Any]]], k: int = 60
) -> List[Dict[str, Any]]:
    """Combine multiple ranking lists using Reciprocal Rank Fusion (RRF).

    Each element in ``rankings`` should be a list of dictionaries representing
    retrieval results ordered from best to worst. Dictionaries must contain a
    unique identifier accessible via the ``url`` key. The final ranking is
    computed using ``1 / (k + rank)`` for each list and aggregated per url.
    ``k`` controls how steeply scores decay with rank.
    """

    scores: Dict[str, float] = defaultdict(float)
    info_by_url: Dict[str, Dict[str, Any]] = {}

    for results in rankings:
        for rank, info in enumerate(results, start=1):
            url = info.get("url")
            if url is None:
                continue
            scores[url] += 1.0 / (k + rank)
            if url not in info_by_url:
                info_by_url[url] = info

    ordered_urls = sorted(scores, key=scores.get, reverse=True)
    return [info_by_url[url] for url in ordered_urls]
