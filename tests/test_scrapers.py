# ruff: noqa: E402
import os
import sys
import types
from datetime import datetime, timezone

# Ensure project root is on the path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Stub snscrape if not installed so import succeeds
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

# Stub PIL.Image used in ingestion utils
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

# Stub pytesseract to avoid heavy dependency
if "pytesseract" not in sys.modules:
    pytesseract = types.ModuleType("pytesseract")

    def image_to_string(_img):
        return ""

    pytesseract.image_to_string = image_to_string
    sys.modules["pytesseract"] = pytesseract

# Stub praw used by RedditScraper
if "praw" not in sys.modules:
    praw = types.ModuleType("praw")

    class Reddit:
        def __init__(self, *a, **k):
            pass

        def subreddit(self, *a, **k):
            return None

    praw.Reddit = Reddit
    sys.modules["praw"] = praw

from tino_storm.ingestion import (
    TwitterScraper,  # noqa: E402
    RedditScraper,  # noqa: E402
    FourChanScraper,  # noqa: E402
)


def test_twitter_scraper(monkeypatch):
    class DummyTweet:
        def __init__(self):
            self.id = 1
            self.date = datetime(2021, 1, 1, tzinfo=timezone.utc)
            self.user = types.SimpleNamespace(username="user")
            self.rawContent = "tweet text"
            self.url = "http://twitter.com/1"
            self.media = None

    class DummyScraper:
        def __init__(self, *a, **k):
            pass

        def get_items(self):
            return [DummyTweet()]

    monkeypatch.setattr("snscrape.modules.twitter.TwitterSearchScraper", DummyScraper)
    results = TwitterScraper().search("query", limit=1)
    assert isinstance(results, list)
    assert results
    assert set(results[0].keys()) == {
        "id",
        "date",
        "author",
        "text",
        "url",
        "images_text",
    }


def test_reddit_scraper(monkeypatch):
    class DummyPost:
        def __init__(self):
            self.id = "a"
            self.created_utc = 1609459200
            self.author = types.SimpleNamespace(name="user")
            self.title = "title"
            self.selftext = "body"
            self.url = "http://example.com/img.jpg"

    class DummySub:
        def search(self, *a, **k):
            return [DummyPost()]

    class DummyReddit:
        def subreddit(self, *a, **k):
            return DummySub()

    monkeypatch.setattr("praw.Reddit", lambda *a, **k: DummyReddit())
    monkeypatch.setattr("tino_storm.ingestion.ocr_image", lambda *a, **k: "")
    scraper = RedditScraper(client_id="x", client_secret="y")
    results = scraper.search("test", "query", limit=1)
    assert isinstance(results, list)
    assert results
    assert set(results[0].keys()) == {
        "id",
        "date",
        "author",
        "title",
        "text",
        "url",
        "images_text",
    }


def test_fourchan_scraper(monkeypatch):
    data = {"posts": [{"no": 1, "time": 1609459200, "name": "anon", "com": "content"}]}

    class DummyResp:
        def json(self):
            return data

        def raise_for_status(self):
            pass

    monkeypatch.setattr("requests.get", lambda *a, **k: DummyResp())
    monkeypatch.setattr("tino_storm.ingestion.ocr_image", lambda *a, **k: "")
    results = FourChanScraper().fetch_thread("g", 123)
    assert isinstance(results, list)
    assert results
    assert set(results[0].keys()) == {"id", "date", "author", "text", "images_text"}
