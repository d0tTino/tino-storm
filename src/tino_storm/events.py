from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
import json


def _default_event_dir() -> Path:
    import os

    return Path(os.getenv("STORM_EVENT_DIR", "events"))


@dataclass
class ResearchAdded:
    vault: str
    path: str
    file_hash: str
    ingested_at: str
    source_url: str


@dataclass
class DocGenerated:
    topic: str
    generated_at: str


def save_event(event: ResearchAdded | DocGenerated, event_dir: Path | None = None) -> Path:
    """Persist ``event`` as a JSON file in ``event_dir``."""
    event_dir = Path(event_dir) if event_dir is not None else _default_event_dir()
    event_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().isoformat()
    file_name = f"{ts}_{event.__class__.__name__}.json"
    path = event_dir / file_name
    path.write_text(json.dumps(asdict(event), default=str))
    return path

