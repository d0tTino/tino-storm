import json
from typing import List

try:  # snscrape may not support our Python version
    import snscrape.modules.twitter as sntwitter
except Exception:  # pragma: no cover - optional dependency
    sntwitter = None

from .utils import ocr_image


class TwitterScraper:
    """Search tweets using snscrape and return a list of dictionaries."""

    def search(self, query: str, limit: int = 20) -> List[dict]:
        global sntwitter
        if not callable(getattr(sntwitter, "TwitterSearchScraper", None)):
            try:  # attempt import again in case dependency loaded later
                import snscrape.modules.twitter as snt
                sntwitter = snt
            except Exception as exc:  # pragma: no cover - optional dependency
                raise RuntimeError("snscrape is required for Twitter scraping") from exc

        scraper = sntwitter.TwitterSearchScraper(query)
        results = []
        for i, tweet in enumerate(scraper.get_items()):
            if i >= limit:
                break
            images_text = []
            media = getattr(tweet, "media", None)
            if media:
                for m in media:
                    if getattr(m, "type", None) == "photo" and getattr(
                        m, "fullUrl", None
                    ):
                        text = ocr_image(m.fullUrl)
                        if text:
                            images_text.append(text)
            results.append(
                {
                    "id": tweet.id,
                    "date": tweet.date.isoformat(),
                    "author": tweet.user.username,
                    "text": tweet.rawContent,
                    "url": tweet.url,
                    "images_text": images_text,
                }
            )
        return results

    def dump_json(self, query: str, limit: int = 20) -> str:
        return json.dumps(self.search(query, limit))
