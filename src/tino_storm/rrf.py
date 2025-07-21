"""Utilities for reciprocal rank fusion of multiple retrievers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Mapping, TypedDict


class ScoreEntry(TypedDict):
    """Internal structure for storing a ranked result."""

    score: float
    result: Mapping
    recency_rank: float | None
    authority_rank: float | None


@dataclass
class RRFRetriever:
    """Combine results from multiple retrievers using Reciprocal Rank Fusion (RRF)."""

    retrievers: Iterable
    k: int = 60
    top_n: int | None = None

    def __post_init__(self) -> None:
        """Ensure retrievers is stored as a list."""
        self.retrievers = list(self.retrievers)

    def forward(
        self, query: str, exclude_urls: Iterable[str] | None = None
    ) -> List[Mapping]:
        """Return fused search results for ``query``."""

        exclude_urls = set(exclude_urls or [])

        scores: dict[str, ScoreEntry] = {}
        for retriever in self.retrievers:
            results = retriever.forward(query, exclude_urls=list(exclude_urls))
            for rank, result in enumerate(results):
                url = result.get("url")
                if not url or url in exclude_urls:
                    continue
                recency_rank = result.get("recency_rank")
                authority_rank = result.get("authority_rank")
                if url not in scores:
                    scores[url] = {
                        "score": 0.0,
                        "result": result,
                        "recency_rank": recency_rank,
                        "authority_rank": authority_rank,
                    }
                else:
                    if recency_rank is not None:
                        existing = scores[url].get("recency_rank")
                        if existing is None or recency_rank < existing:
                            scores[url]["recency_rank"] = recency_rank
                    if authority_rank is not None:
                        existing = scores[url].get("authority_rank")
                        if existing is None or authority_rank < existing:
                            scores[url]["authority_rank"] = authority_rank
                scores[url]["score"] += 1.0 / (rank + 1 + self.k)

        ranked: List[ScoreEntry] = sorted(
            scores.values(),
            key=lambda x: (
                -x["score"],
                x.get("recency_rank", float("inf")),
                x.get("authority_rank", float("inf")),
            ),
        )
        fused = [entry["result"] for entry in ranked]
        if self.top_n is not None:
            fused = fused[: self.top_n]
        return fused
