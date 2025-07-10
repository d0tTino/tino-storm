from datetime import datetime


from tino_storm import loaders


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
