import types
from tino_storm.loaders import twitter


def test_ocr_image_uses_context(monkeypatch):
    called = {}

    class DummyResp:
        def __init__(self):
            self.content = b"img"
        def raise_for_status(self):
            called['raise'] = True
        def __enter__(self):
            called['enter'] = True
            return self
        def __exit__(self, exc_type, exc, tb):
            called['exit'] = True

    def fake_get(url, timeout=10):
        called['url'] = url
        called['timeout'] = timeout
        return DummyResp()

    monkeypatch.setattr(twitter.requests, "get", fake_get, raising=False)

    class DummyImg:
        def __enter__(self):
            called['img_enter'] = True
            return self
        def __exit__(self, exc_type, exc, tb):
            called['img_exit'] = True

    def fake_open(data):
        called['data'] = data.getvalue()
        return DummyImg()

    monkeypatch.setattr(twitter, "Image", types.SimpleNamespace(open=fake_open))
    monkeypatch.setattr(twitter, "pytesseract", types.SimpleNamespace(image_to_string=lambda img: "txt"))

    result = twitter._ocr_image("http://example.com/img")
    assert result == "txt"
    assert called['enter'] and called['exit']
    assert called['img_enter'] and called['img_exit']
    assert called['data'] == b"img"
