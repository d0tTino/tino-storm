"""Utilities for reciprocal rank fusion of multiple retrievers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Mapping, TypedDict


class ScoreEntry(TypedDict):
    """Internal structure for storing a ranked result."""

    score: float
    result: Mapping


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
                if url not in scores:
                    scores[url] = {"score": 0.0, "result": result}
                scores[url]["score"] += 1.0 / (rank + 1 + self.k)

        ranked: List[ScoreEntry] = sorted(
            scores.values(), key=lambda x: x["score"], reverse=True
        )
        fused = [entry["result"] for entry in ranked]
        if self.top_n is not None:
            fused = fused[: self.top_n]
        return fused
