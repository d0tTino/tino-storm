"""Reddit loader using praw with Pushshift fallback."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

import requests

try:
    import praw  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    praw = None


@dataclass
class RedditRecord:
    text: str
    url: str
    timestamp: datetime
    images: List[str]


def _extract_post_id(url: str) -> str:
    parts = url.rstrip("/").split("/")
    for part in reversed(parts):
        if part and part != "comments":
            return part.split("?")[0]
    raise ValueError(f"Cannot parse post id from {url}")


def _fetch_pushshift(post_id: str) -> Optional[dict]:
    try:
        resp = requests.get(
            f"https://api.pushshift.io/reddit/search/submission/?ids={post_id}",
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json().get("data")
        return data[0] if data else None
    except Exception:
        return None


def fetch_post(
    url: str, client_id: str | None = None, client_secret: str | None = None
) -> List[RedditRecord]:
    """Fetch a reddit submission given its ``url``."""
    post_id = _extract_post_id(url)
    text = ""
    images: List[str] = []
    ts = datetime.utcnow()

    if praw is not None and client_id and client_secret:
        try:
            reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent="tino-storm",
            )
            submission = reddit.submission(id=post_id)
            text = submission.selftext or submission.title
            ts = datetime.fromtimestamp(submission.created_utc)
            if submission.url.lower().endswith((".jpg", ".png", ".gif")):
                images.append(submission.url)
        except Exception:
            pass

    if not text:
        data = _fetch_pushshift(post_id)
        if data:
            text = data.get("selftext") or data.get("title") or ""
            ts = datetime.fromtimestamp(
                data.get("created_utc", datetime.utcnow().timestamp())
            )
            if isinstance(data.get("url"), str) and data["url"].lower().endswith(
                (".jpg", ".png", ".gif")
            ):
                images.append(data["url"])

    return [RedditRecord(text=text, url=url, timestamp=ts, images=images)]
