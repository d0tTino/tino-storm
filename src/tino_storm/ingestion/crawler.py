import json
from typing import Dict, List

import requests
import trafilatura

from ..security import log_request


class WebCrawler:
    """Fetch web pages and extract text with ``trafilatura``."""

    def fetch(self, url: str) -> Dict[str, str]:
        """Return a dictionary containing ``url`` and extracted ``text``."""
        try:
            log_request("GET", url)
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            html = resp.text
        except Exception:
            html = ""
        text = trafilatura.extract(html) or ""
        return {"url": url, "text": text}

    def fetch_many(self, urls: List[str]) -> List[Dict[str, str]]:
        return [self.fetch(u) for u in urls]

    def dump_json(self, urls: List[str]) -> str:
        return json.dumps(self.fetch_many(urls))
