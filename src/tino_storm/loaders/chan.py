"""4chan loader using the JSON API."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List
from urllib.parse import urlparse

import requests


@dataclass
class ChanRecord:
    text: str
    url: str
    timestamp: datetime
    images: List[str]


def _parse_url(url: str) -> tuple[str, str]:
    parsed = urlparse(url)
    parts = parsed.path.strip("/").split("/")
    if len(parts) < 3:
        raise ValueError(f"Invalid 4chan url: {url}")
    board = parts[0]
    thread_id = parts[2]
    return board, thread_id


def fetch_thread(url: str) -> List[ChanRecord]:
    """Fetch a 4chan thread given its ``url``."""
    board, thread_id = _parse_url(url)
    resp = requests.get(
        f"https://a.4cdn.org/{board}/thread/{thread_id}.json", timeout=10
    )
    resp.raise_for_status()
    data = resp.json()
    records: List[ChanRecord] = []
    for post in data.get("posts", []):
        text = post.get("com", "")
        ts = datetime.fromtimestamp(post.get("time", 0))
        images = []
        if "tim" in post and "ext" in post:
            images.append(f"https://i.4cdn.org/{board}/{post['tim']}{post['ext']}")
        post_url = f"{url}#{post['no']}"
        records.append(ChanRecord(text=text, url=post_url, timestamp=ts, images=images))
    return records
