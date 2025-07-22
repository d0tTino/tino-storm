from datetime import datetime
import os
import base64
import json
from pathlib import Path
import pytest

from tino_storm.loaders import reddit, chan


from tino_storm import loaders
from tino_storm.loaders import generic


def test_choose_loader_twitter():
    assert (
        loaders._choose_loader("https://twitter.com/user/status/1")
        is loaders.twitter.fetch_tweet
    )


def test_choose_loader_reddit():
    assert (
        loaders._choose_loader("https://www.reddit.com/r/test/comments/abc/post/")
        is loaders.reddit.fetch_post
    )


def test_choose_loader_chan():
    assert (
        loaders._choose_loader("https://boards.4chan.org/g/thread/123")
        is loaders.chan.fetch_thread
    )


def test_choose_loader_4channel():
    assert (
        loaders._choose_loader("https://boards.4channel.org/g/thread/123")
        is loaders.chan.fetch_thread
    )


def test_choose_loader_generic_url():
    assert (
        loaders._choose_loader("https://example.com/page") is loaders.generic.fetch_url
    )


def test_choose_loader_file():
    path = "tests/data/sample.html"
    assert loaders._choose_loader(path) is loaders.generic.fetch_url


def test_load_dispatch(monkeypatch):
    called = {}

    def fake(url: str):
        called["url"] = url
        return [
            loaders.Record(
                text="hi", url=url, timestamp=datetime(2020, 1, 1), images=[]
            )
        ]

    monkeypatch.setattr(loaders, "_choose_loader", lambda url: fake)
    result = loaders.load("http://example.com")
    assert called["url"] == "http://example.com"
    assert result == [
        {
            "text": "hi",
            "url": "http://example.com",
            "timestamp": datetime(2020, 1, 1),
            "images": [],
        }
    ]


def test_generic_loader_local(monkeypatch):
    called = {}

    def fake_ocr(url: str) -> str:
        called["img"] = url
        return "ocr"

    monkeypatch.setattr(generic, "_ocr_image", fake_ocr)

    img_path = "tests/data/text.png"
    file_path = "tests/data/sample.html"
    # Minimal 1x1 PNG image
    png_data = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMB/6XebvIAAAAASUVORK5CYII="
    )
    with open(img_path, "wb") as f:
        f.write(png_data)
    try:
        records = generic.fetch_url(file_path)
        assert records[0].url == file_path
        assert "Hello World" in records[0].text
        assert "ocr" in records[0].text
        assert records[0].images == ["file://" + os.path.abspath(img_path)]
    finally:
        os.remove(img_path)


@pytest.mark.parametrize(
    "json_file,loader,url,expected",
    [
        (
            "reddit_pushshift.json",
            reddit.fetch_post,
            "https://www.reddit.com/r/test/comments/abc/post/",
            {
                "text": "Hello Reddit",
                "url": "https://www.reddit.com/r/test/comments/abc/post/",
                "timestamp": datetime.fromtimestamp(1609459200),
                "images": ["https://i.redd.it/test.png"],
            },
        ),
        (
            "chan_thread.json",
            chan.fetch_thread,
            "https://boards.4chan.org/g/thread/123",
            {
                "text": "First post",
                "url": "https://boards.4chan.org/g/thread/123#123456",
                "timestamp": datetime.fromtimestamp(1609459200),
                "images": ["https://i.4cdn.org/g/123456789.png"],
            },
        ),
    ],
)
def test_loaders_from_samples(monkeypatch, json_file, loader, url, expected):
    sample_path = Path("tests/data") / json_file

    class FakeResponse:
        def __init__(self, data):
            self._data = data

        def json(self):
            return self._data

        def raise_for_status(self):
            pass

    with open(sample_path) as f:
        data = json.load(f)

    target_module = reddit if loader is reddit.fetch_post else chan
    monkeypatch.setattr(
        target_module.requests,
        "get",
        lambda *a, **k: FakeResponse(data),
        raising=False,
    )
    if loader is reddit.fetch_post:
        monkeypatch.setattr(reddit, "praw", None)

    records = loader(url)
    record = records[0]
    assert record.text == expected["text"]
    assert record.url == expected["url"]
    assert record.timestamp == expected["timestamp"]
    assert record.images == expected["images"]
