import datetime
from unittest.mock import patch

import types

import pytest

ROOT_DIR = None
import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
SRC_DIR = os.path.join(ROOT_DIR, "src")
if os.path.isdir(SRC_DIR) and SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# Stub external modules so importing ingestion does not require heavy deps
sys.modules.setdefault("snscrape", types.ModuleType("snscrape"))
sys.modules.setdefault("snscrape.modules", types.ModuleType("snscrape.modules"))
twitter_mod = types.ModuleType("snscrape.modules.twitter")
twitter_mod.TwitterSearchScraper = object
sys.modules.setdefault("snscrape.modules.twitter", twitter_mod)

from tino_storm.ingestion import TwitterScraper, RedditScraper, FourChanScraper


class DummyTweet:
    def __init__(self):
        self.id = 1
        self.date = datetime.datetime(2021, 1, 1, 0, 0, 0)
        self.user = type("U", (), {"username": "tester"})
        self.rawContent = "text"
        self.url = "http://t.co/1"
        self.media = [type("M", (), {"type": "photo", "fullUrl": "http://img"})]


def test_twitter_scraper():
    with patch("snscrape.modules.twitter.TwitterSearchScraper") as Scraper:
        Scraper.return_value.get_items.return_value = [DummyTweet()]
        with patch("tino_storm.ingestion.twitter.ocr_image", return_value="ocr"):
            scraper = TwitterScraper()
            data = scraper.search("test", limit=1)
            assert data[0]["author"] == "tester"
            assert data[0]["images_text"] == ["ocr"]


class DummyRedditPost:
    id = "abc"
    created_utc = 1609459200
    author = type("A", (), {"name": "redditor"})
    title = "title"
    selftext = "body"
    url = "http://img.png"


def test_reddit_scraper_praw():
    with patch("praw.Reddit") as Reddit:
        Reddit.return_value.subreddit.return_value.search.return_value = [
            DummyRedditPost
        ]
        with patch("tino_storm.ingestion.reddit.ocr_image", return_value="ocr"):
            scraper = RedditScraper(client_id="a", client_secret="b")
            data = scraper.search("sub", "q", limit=1)
            assert data[0]["title"] == "title"
            assert data[0]["images_text"] == ["ocr"]


def test_reddit_scraper_pushshift():
    with patch("praw.Reddit", side_effect=Exception):
        with patch("requests.get") as g:
            g.return_value.status_code = 200
            g.return_value.json.return_value = {
                "data": [
                    {
                        "id": "def",
                        "created_utc": 1609459200,
                        "author": "user",
                        "title": "t",
                        "selftext": "b",
                        "url": "http://img.png",
                    }
                ]
            }
            with patch("tino_storm.ingestion.reddit.ocr_image", return_value="ocr"):
                scraper = RedditScraper(client_id="a", client_secret="b")
                data = scraper.search("sub", "q", limit=1)
                assert data[0]["id"] == "def"


def test_fourchan_scraper():
    with patch("requests.get") as g:
        g.return_value.status_code = 200
        g.return_value.json.return_value = {
            "posts": [
                {
                    "no": 123,
                    "time": 1609459200,
                    "name": "anon",
                    "com": "hello",
                    "tim": "abc",
                    "ext": ".jpg",
                }
            ]
        }
        with patch("tino_storm.ingestion.fourchan.ocr_image", return_value="ocr"):
            scraper = FourChanScraper()
            data = scraper.fetch_thread("g", 1)
            assert data[0]["author"] == "anon"
            assert data[0]["images_text"] == ["ocr"]
