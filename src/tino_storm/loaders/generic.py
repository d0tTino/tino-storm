"""Generic web crawler with optional OCR via pytesseract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from typing import List
from urllib.parse import urljoin, urlparse
import os

import requests

try:
    import trafilatura  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    trafilatura = None

try:
    import pytesseract  # type: ignore
    from PIL import Image
except Exception:  # pragma: no cover - optional dependency
    pytesseract = None
    Image = None

from bs4 import BeautifulSoup  # type: ignore


@dataclass
class GenericRecord:
    text: str
    url: str
    timestamp: datetime
    images: List[str]


def _ocr_image(url: str) -> str:
    """Return OCR text for an image URL or file path."""
    if not pytesseract or not Image:  # pragma: no cover - optional dependency
        return ""
    try:
        if url.startswith("http://") or url.startswith("https://"):
            with requests.get(url, timeout=10) as resp:
                resp.raise_for_status()
                with Image.open(BytesIO(resp.content)) as img:
                    return pytesseract.image_to_string(img)
        else:
            path = url
            if url.startswith("file://"):
                path = url[7:]
            with open(path, "rb") as f:
                with Image.open(f) as img:
                    return pytesseract.image_to_string(img)
    except Exception:  # pragma: no cover - ignore OCR errors
        return ""


def fetch_url(url: str) -> List[GenericRecord]:
    """Fetch a generic web page or local HTML file."""
    parsed = urlparse(url)
    if parsed.scheme in ("file", ""):
        path = parsed.path if parsed.scheme == "file" else url
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            html = f.read()
        base = f"file://{os.path.abspath(path)}"
    else:
        if trafilatura is None:  # pragma: no cover - optional dependency
            raise ImportError("trafilatura is required for generic scraping")
        html = trafilatura.fetch_url(url)
        if not html:
            raise ValueError(f"Unable to fetch url: {url}")
        base = url
    text = trafilatura.extract(html) if trafilatura is not None else None
    if not text:
        text = BeautifulSoup(html, "html.parser").get_text()
    soup = BeautifulSoup(html, "html.parser")
    images: List[str] = []
    for tag in soup.find_all("img"):
        src = tag.get("src")
        if not src:
            continue
        img_url = urljoin(base, src)
        images.append(img_url)
        text += _ocr_image(img_url)
    return [GenericRecord(text=text, url=url, timestamp=datetime.utcnow(), images=images)]
