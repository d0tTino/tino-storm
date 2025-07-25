"""Simple helper to fetch arXiv papers."""

from __future__ import annotations

import json
from io import BytesIO
from typing import Dict, List

import requests

from ..security import log_request

try:  # optional dependency
    import arxiv  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    arxiv = None  # type: ignore

try:
    from pypdf import PdfReader  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    try:
        from PyPDF2 import PdfReader  # type: ignore
    except Exception:  # pragma: no cover - optional dependency
        PdfReader = None  # type: ignore


class ArxivScraper:
    """Fetch paper metadata and PDF text from arXiv."""

    def _pdf_text(self, url: str) -> str:
        if PdfReader is None:
            return ""
        try:
            log_request("GET", url)
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            reader = PdfReader(BytesIO(resp.content))
            return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
        except Exception:
            return ""

    def fetch(self, arxiv_id: str) -> Dict[str, str]:
        global arxiv
        if not callable(getattr(arxiv, "Search", None)):
            try:
                import arxiv as arxiv_mod  # type: ignore

                arxiv = arxiv_mod
            except Exception as exc:  # pragma: no cover - optional dependency
                raise RuntimeError(
                    "arxiv package is required for Arxiv scraping"
                ) from exc

        client = arxiv.Client()
        search = arxiv.Search(id_list=[arxiv_id])
        result = next(client.results(search), None)
        if result is None:
            raise ValueError(f"Paper {arxiv_id} not found")
        pdf_text = (
            self._pdf_text(result.pdf_url) if getattr(result, "pdf_url", None) else ""
        )
        return {
            "id": arxiv_id,
            "title": getattr(result, "title", ""),
            "summary": getattr(result, "summary", ""),
            "url": getattr(result, "entry_id", ""),
            "pdf_text": pdf_text,
        }

    def fetch_many(self, ids: List[str]) -> List[Dict[str, str]]:
        return [self.fetch(i) for i in ids]

    def dump_json(self, ids: List[str]) -> str:
        return json.dumps(self.fetch_many(ids))
