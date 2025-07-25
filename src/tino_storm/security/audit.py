from __future__ import annotations

from datetime import datetime
from pathlib import Path

AUDIT_LOG_PATH = Path.home() / ".tino_storm" / "audit.log"


def log_request(method: str, url: str) -> None:
    """Append an entry to the audit log for the given request."""
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().isoformat()
    with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} {method.upper()} {url}\n")
