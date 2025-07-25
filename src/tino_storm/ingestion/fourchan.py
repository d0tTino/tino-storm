import json
from datetime import datetime
from typing import List

import requests

from ..security import log_request

from .utils import ocr_image


class FourChanScraper:
    """Scrape threads from 4chan's JSON API."""

    API_URL = "https://a.4cdn.org/{board}/thread/{thread}.json"

    def fetch_thread(self, board: str, thread_no: int) -> List[dict]:
        url = self.API_URL.format(board=board, thread=thread_no)
        log_request("GET", url)
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        posts = []
        for p in data.get("posts", []):
            images_text = []
            if "tim" in p and "ext" in p:
                img_url = f"https://i.4cdn.org/{board}/{p['tim']}{p['ext']}"
                text = ocr_image(img_url)
                if text:
                    images_text.append(text)
            posts.append(
                {
                    "id": p.get("no"),
                    "date": datetime.utcfromtimestamp(p.get("time", 0)).isoformat(),
                    "author": p.get("name"),
                    "text": p.get("com"),
                    "images_text": images_text,
                }
            )
        return posts

    def dump_json(self, board: str, thread_no: int) -> str:
        return json.dumps(self.fetch_thread(board, thread_no))
