# ruff: noqa: E402
import os
import sys
import types

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Stub arxiv if missing
if "arxiv" not in sys.modules:
    arxiv = types.ModuleType("arxiv")

    class Search:
        def __init__(self, *a, **k):
            pass

    class Result:
        def __init__(self):
            self.entry_id = "http://arxiv.org/abs/1234"
            self.title = "title"
            self.summary = "summary"
            self.pdf_url = "http://example.com/paper.pdf"

    class Client:
        def __init__(self, *a, **k):
            pass

        def results(self, *_a, **_k):
            yield Result()

    arxiv.Search = Search
    arxiv.Client = Client
    sys.modules["arxiv"] = arxiv

# Stub PdfReader
if "pypdf" not in sys.modules:
    pypdf = types.ModuleType("pypdf")

    class DummyReader:
        def __init__(self, *a, **k):
            self.pages = [types.SimpleNamespace(extract_text=lambda: "pdf text")]

    pypdf.PdfReader = DummyReader
    sys.modules["pypdf"] = pypdf
    sys.modules.setdefault("PyPDF2", pypdf)

from tino_storm.ingestion import ArxivScraper  # noqa: E402
from tino_storm.ingest.watcher import VaultIngestHandler  # noqa: E402


def test_arxiv_scraper(monkeypatch):
    def fake_get(*a, **k):
        return types.SimpleNamespace(content=b"data", raise_for_status=lambda: None)

    monkeypatch.setattr("requests.get", fake_get, raising=False)
    scraper = ArxivScraper()
    res = scraper.fetch("1234")
    assert res["pdf_text"] == "pdf text"
    assert res["title"] == "title"


class DummyScraper:
    def __init__(self, results):
        self._results = results

    def fetch_many(self, ids):
        return self._results


def test_handle_arxiv(monkeypatch, tmp_path):
    res = [{"title": "t", "summary": "s", "pdf_text": "p", "url": "u"}]
    root = tmp_path / "vault"
    vault = root / "topic"
    vault.mkdir(parents=True)
    file = vault / "ids.arxiv"
    file.write_text("1234\n")
    handler = VaultIngestHandler(str(root))
    captured = []
    monkeypatch.setattr(
        handler, "_ingest_text", lambda t, s, v: captured.append((t, s, v))
    )
    monkeypatch.setattr(
        "tino_storm.ingest.watcher.ArxivScraper", lambda *a, **k: DummyScraper(res)
    )
    handler._handle_file(file, "topic")
    assert captured and captured[0][0].startswith("t")
