# ruff: noqa: E402
import os
import sys
import types
from datetime import datetime, timezone

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Stub optional dependencies similar to existing scraper tests
if "snscrape.modules.twitter" not in sys.modules:
    snscrape = types.ModuleType("snscrape")
    modules = types.ModuleType("snscrape.modules")
    twitter = types.ModuleType("snscrape.modules.twitter")
    twitter.TwitterSearchScraper = None
    modules.twitter = twitter
    snscrape.modules = modules
    sys.modules["snscrape"] = snscrape
    sys.modules["snscrape.modules"] = modules
    sys.modules["snscrape.modules.twitter"] = twitter

if "praw" not in sys.modules:
    praw = types.ModuleType("praw")

    class Reddit:
        def subreddit(self, *a, **k):
            return None

    praw.Reddit = Reddit
    sys.modules["praw"] = praw

# Stub PIL and pytesseract used in ingestion utils
if "PIL" not in sys.modules:
    pil = types.ModuleType("PIL")
    image_mod = types.ModuleType("PIL.Image")

    class Image:
        def __init__(self, *a, **k):
            pass

        @staticmethod
        def open(*a, **k):
            return Image()

    image_mod.Image = Image
    pil.Image = Image
    sys.modules["PIL"] = pil
    sys.modules["PIL.Image"] = image_mod

if "pytesseract" not in sys.modules:
    pytesseract = types.ModuleType("pytesseract")

    def image_to_string(_img):
        return ""

    pytesseract.image_to_string = image_to_string
    sys.modules["pytesseract"] = pytesseract

# Stub arxiv and PdfReader for ArxivScraper
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
        def results(self, *_a, **_k):
            yield Result()

    arxiv.Search = Search
    arxiv.Client = Client
    sys.modules["arxiv"] = arxiv

if "pypdf" not in sys.modules:
    pypdf = types.ModuleType("pypdf")

    class DummyReader:
        def __init__(self, *a, **k):
            self.pages = [types.SimpleNamespace(extract_text=lambda: "pdf text")]

    pypdf.PdfReader = DummyReader
    sys.modules["pypdf"] = pypdf
    sys.modules.setdefault("PyPDF2", pypdf)

from tino_storm.ingestion import (
    ArxivScraper,
    TwitterScraper,
    RedditScraper,
    FourChanScraper,
)


def test_arxiv_keys(monkeypatch):
    monkeypatch.setattr(
        "requests.get",
        lambda *a, **k: types.SimpleNamespace(
            content=b"data", raise_for_status=lambda: None
        ),
        raising=False,
    )
    result = ArxivScraper().fetch("1234")
    assert {"title", "summary", "url", "pdf_text"} <= result.keys()


def test_twitter_keys(monkeypatch):
    class DummyTweet:
        def __init__(self):
            self.id = 1
            self.date = datetime(2021, 1, 1, tzinfo=timezone.utc)
            self.user = types.SimpleNamespace(username="user")
            self.rawContent = "tweet text"
            self.url = "http://twitter.com/1"
            self.media = None

    class DummyScraper:
        def get_items(self):
            return [DummyTweet()]

    monkeypatch.setattr(
        "snscrape.modules.twitter.TwitterSearchScraper",
        lambda *a, **k: DummyScraper(),
    )
    results = TwitterScraper().search("q", limit=1)
    assert {"text", "url", "date"} <= results[0].keys()


def test_reddit_keys(monkeypatch):
    class DummyPost:
        def __init__(self):
            self.id = "a"
            self.created_utc = 1609459200
            self.author = types.SimpleNamespace(name="user")
            self.title = "title"
            self.selftext = "body"
            self.url = "http://example.com"

    class DummySub:
        def search(self, *a, **k):
            return [DummyPost()]

    class DummyReddit:
        def subreddit(self, *a, **k):
            return DummySub()

    monkeypatch.setattr("praw.Reddit", lambda *a, **k: DummyReddit())
    monkeypatch.setattr("tino_storm.ingestion.ocr_image", lambda *a, **k: "")
    results = RedditScraper(client_id="x", client_secret="y").search(
        "test", "q", limit=1
    )
    assert {"text", "url", "date"} <= results[0].keys()


def test_fourchan_keys(monkeypatch):
    data = {"posts": [{"no": 1, "time": 1609459200, "name": "anon", "com": "text"}]}

    class DummyResp:
        def json(self):
            return data

        def raise_for_status(self):
            pass

    monkeypatch.setattr("requests.get", lambda *a, **k: DummyResp())
    monkeypatch.setattr("tino_storm.ingestion.ocr_image", lambda *a, **k: "")
    results = FourChanScraper().fetch_thread("g", 1)
    assert {"text", "date"} <= results[0].keys()
