"""Loader helpers for scraping supported URLs."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any
from urllib.parse import urlparse


@dataclass
class Record:
    """Standardized scraped record."""

    text: str
    url: str
    timestamp: datetime
    images: list[str]


def _choose_loader(url: str):
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()
    if "twitter.com" in netloc or "x.com" in netloc:
        from . import twitter

        return twitter.fetch_tweet
    if "reddit.com" in netloc:
        from . import reddit

        return reddit.fetch_post
    if "4chan.org" in netloc or "4channel.org" in netloc:
        from . import chan

        return chan.fetch_thread
    if parsed.scheme in ("http", "https", "file") or (parsed.scheme == "" and parsed.path):
        from . import generic

        return generic.fetch_url
    raise ValueError(f"No loader for URL: {url}")


def load(url: str) -> list[dict[str, Any]]:
    """Return scraped records for ``url`` as dictionaries."""
    loader = _choose_loader(url)
    records = loader(url)
    return [asdict(r) for r in records]
