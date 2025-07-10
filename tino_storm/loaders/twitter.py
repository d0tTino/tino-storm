"""Twitter loader using snscrape with optional OCR via pytesseract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from typing import List

import requests

try:
    import snscrape.modules.twitter as sntwitter  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    sntwitter = None

try:
    import pytesseract  # type: ignore
    from PIL import Image
except Exception:  # pragma: no cover - optional dependency
    pytesseract = None
    Image = None


@dataclass
class TweetRecord:
    text: str
    url: str
    timestamp: datetime
    images: List[str]


def _ocr_image(url: str) -> str:
    if not pytesseract or not Image:  # pragma: no cover - optional dependency
        return ""
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        with Image.open(BytesIO(resp.content)) as img:
            return pytesseract.image_to_string(img)
    except Exception:
        return ""


def fetch_tweet(url: str) -> List[TweetRecord]:
    """Fetch a tweet given its ``url``."""
    if sntwitter is None:  # pragma: no cover - optional dependency
        raise ImportError("snscrape is required for twitter scraping")
    tweet_id = url.rstrip("/").split("/")[-1].split("?")[0]
    scraper = sntwitter.TwitterTweetScraper(tweet_id)
    try:
        tweet = next(scraper.get_items())
    except StopIteration:
        raise ValueError(f"Tweet not found: {url}")
    text = tweet.rawContent or ""
    images = [m.fullUrl for m in (tweet.media or []) if hasattr(m, "fullUrl")]
    if not text:
        for img in images:
            text += _ocr_image(img)
    return [TweetRecord(text=text, url=url, timestamp=tweet.date, images=images)]
