import sys
import types

if "snscrape.modules.twitter" not in sys.modules:
    mod = types.ModuleType("snscrape.modules.twitter")

    class _DummyScraper:
        def __init__(self, *a, **k):
            pass

        def get_items(self):
            return []

    mod.TwitterSearchScraper = _DummyScraper
    pkg = types.ModuleType("snscrape.modules")
    setattr(pkg, "twitter", mod)
    sys.modules["snscrape"] = types.ModuleType("snscrape")
    sys.modules["snscrape.modules"] = pkg
    sys.modules["snscrape.modules.twitter"] = mod

from tino_storm.ingest.watcher import VaultIngestHandler


class DummyScraper:
    def __init__(self, results):
        self._results = results

    def search(self, *a, limit=20, **k):
        return self._results

    def fetch_thread(self, *a, **k):
        return self._results


def _run_handler(tmp_path, filename, content, monkeypatch, scraper_attr, results):
    root = tmp_path / "vault"
    vault = root / "topic"
    vault.mkdir(parents=True)
    file = vault / filename
    file.write_text(content)
    handler = VaultIngestHandler(str(root))
    captured = []
    monkeypatch.setattr(
        handler, "_ingest_text", lambda text, src, v: captured.append((text, src, v))
    )
    monkeypatch.setattr(
        "tino_storm.ingest.watcher." + scraper_attr,
        lambda *a, **k: DummyScraper(results),
    )
    handler._handle_file(file, "topic")
    return captured


def test_handle_twitter(monkeypatch, tmp_path):
    res = [{"text": "t", "url": "u"}]
    captured = _run_handler(
        tmp_path,
        "q.twitter",
        "q",
        monkeypatch,
        "TwitterScraper",
        res,
    )
    assert captured and captured[0][0].startswith("t")


def test_handle_reddit(monkeypatch, tmp_path):
    res = [{"title": "ti", "text": "tx", "url": "u"}]
    captured = _run_handler(
        tmp_path,
        "r.reddit",
        "sub\nquery",
        monkeypatch,
        "RedditScraper",
        res,
    )
    assert any("ti" in c[0] for c in captured)


def test_handle_fourchan(monkeypatch, tmp_path):
    res = [{"text": "p"}]
    captured = _run_handler(
        tmp_path,
        "f.4chan",
        "b\n123",
        monkeypatch,
        "FourChanScraper",
        res,
    )
    assert captured[0][0] == "p"
