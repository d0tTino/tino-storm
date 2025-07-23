import json
from datetime import datetime
from typing import List, Optional

import praw
import requests

from .utils import ocr_image


class RedditScraper:
    """Fetch posts from Reddit using praw with Pushshift fallback."""

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        user_agent: str = "storm",
    ) -> None:
        try:
            self.reddit = praw.Reddit(
                client_id=client_id, client_secret=client_secret, user_agent=user_agent
            )
        except Exception:
            self.reddit = None

    def _post_to_dict(self, post) -> dict:
        images_text = []
        if post.url and post.url.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
            text = ocr_image(post.url)
            if text:
                images_text.append(text)
        return {
            "id": post.id,
            "date": datetime.utcfromtimestamp(post.created_utc).isoformat(),
            "author": getattr(post.author, "name", None),
            "title": post.title,
            "text": getattr(post, "selftext", ""),
            "url": post.url,
            "images_text": images_text,
        }

    def _pushshift_search(self, subreddit: str, query: str, limit: int) -> List[dict]:
        url = "https://api.pushshift.io/reddit/search/submission"
        params = {"subreddit": subreddit, "q": query, "size": limit}
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        results = []
        for item in data:
            images_text = []
            if item.get("url", "").lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
                text = ocr_image(item["url"])
                if text:
                    images_text.append(text)
            results.append(
                {
                    "id": item.get("id"),
                    "date": datetime.utcfromtimestamp(
                        item.get("created_utc", 0)
                    ).isoformat(),
                    "author": item.get("author"),
                    "title": item.get("title"),
                    "text": item.get("selftext", ""),
                    "url": item.get("url"),
                    "images_text": images_text,
                }
            )
        return results

    def search(self, subreddit: str, query: str, limit: int = 20) -> List[dict]:
        if self.reddit is not None:
            try:
                sub = self.reddit.subreddit(subreddit)
                posts = sub.search(query, limit=limit)
                return [self._post_to_dict(p) for p in posts]
            except Exception:
                pass
        return self._pushshift_search(subreddit, query, limit)

    def dump_json(self, subreddit: str, query: str, limit: int = 20) -> str:
        return json.dumps(self.search(subreddit, query, limit))
