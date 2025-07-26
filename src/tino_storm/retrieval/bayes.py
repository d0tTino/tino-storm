from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List


def update_posterior(info: Dict[str, Any], prior: float = 0.5) -> float:
    """Return an updated posterior score based on recency and citations."""
    meta = info.get("meta", info)

    recency_factor = 1.0
    date_val = meta.get("date") or meta.get("timestamp")
    if date_val:
        try:
            dt = date_val
            if not isinstance(dt, datetime):
                dt = datetime.fromisoformat(str(dt))
            dt = dt.replace(tzinfo=dt.tzinfo or timezone.utc)
            age_days = (datetime.now(timezone.utc) - dt).total_seconds() / 86400
            recency_factor = 1.0 / (1.0 + max(age_days, 0.0))
        except Exception:
            recency_factor = 1.0

    citation_factor = 1.0 + float(meta.get("citations", meta.get("karma", 0)) or 0)

    return prior * recency_factor * citation_factor


def add_posteriors(
    results: List[Dict[str, Any]], prior: float = 0.5
) -> List[Dict[str, Any]]:
    """Attach posterior scores to a list of result dictionaries."""
    updated = []
    for r in results:
        info = dict(r)
        info["posterior"] = update_posterior(info, prior)
        updated.append(info)
    return updated
