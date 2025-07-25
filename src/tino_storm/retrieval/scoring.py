from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List


def compute_score(info: Dict[str, Any]) -> float:
    """Return a numeric score for a search result.

    The score combines recency, citation/karma and model confidence.
    ``info`` may contain a ``meta`` dictionary where these values are stored.
    """
    meta = info.get("meta", info)

    # recency score based on days since timestamp/date
    recency_score = 0.0
    date_val = meta.get("date") or meta.get("timestamp")
    if date_val:
        try:
            dt = date_val
            if not isinstance(dt, datetime):
                dt = datetime.fromisoformat(str(dt))
            dt = dt.replace(tzinfo=dt.tzinfo or timezone.utc)
            age_days = (datetime.now(timezone.utc) - dt).total_seconds() / 86400
            recency_score = 1.0 / (1.0 + max(age_days, 0.0))
        except Exception:
            recency_score = 0.0

    # citation/karma score
    citation_score = float(meta.get("citations", meta.get("karma", 0)) or 0)

    # model confidence score
    confidence_score = float(
        meta.get("confidence", meta.get("model_confidence", 0)) or 0
    )

    return recency_score + citation_score + confidence_score


def score_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Compute scores for ``results`` and return them sorted by score."""
    scored = []
    for r in results:
        info = dict(r)
        info["score"] = compute_score(info)
        scored.append(info)
    return sorted(scored, key=lambda x: x["score"], reverse=True)
