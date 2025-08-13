from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ResearchResult:
    """Structured result returned from research providers."""

    url: str
    snippets: List[str]
    meta: Dict[str, Any] = field(default_factory=dict)
    summary: Optional[str] = None


def as_research_result(data: Dict[str, Any]) -> ResearchResult:
    """Convert a mapping to ``ResearchResult`` ignoring extra keys."""

    return ResearchResult(
        url=data.get("url", ""),
        snippets=data.get("snippets", []),
        meta=data.get("meta", {}),
        summary=data.get("summary"),
    )
