import pytest
from fastapi.testclient import TestClient

from tino_storm import fastapi_app
from tino_storm.storm import Storm


class _Doc:
    def __init__(self, text: str) -> None:
        self.text = text

    def to_string(self) -> str:
        return self.text


def _patch_storm(monkeypatch: pytest.MonkeyPatch) -> None:
    orig_build_outline = Storm.build_outline
    orig_run_pipeline = Storm.run_pipeline

    def build_outline(
        self, topic: str, ground_truth_url: str = "", callback_handler=None
    ):
        text = orig_build_outline(self, topic, ground_truth_url, callback_handler)
        return _Doc(text)

    def run_pipeline(
        self,
        topic: str,
        ground_truth_url: str = "",
        remove_duplicate: bool = False,
        callback_handler=None,
    ):
        text = orig_run_pipeline(
            self, topic, ground_truth_url, remove_duplicate, callback_handler
        )
        return _Doc(text)

    monkeypatch.setattr(Storm, "build_outline", build_outline)
    monkeypatch.setattr(Storm, "run_pipeline", run_pipeline)


def test_outline_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_storm(monkeypatch)
    client = TestClient(fastapi_app.app)
    resp = client.post("/outline", json={"topic": "topic"})
    assert resp.status_code == 200
    assert resp.json() == {"outline": "outline:topic"}


def test_article_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_storm(monkeypatch)
    client = TestClient(fastapi_app.app)
    resp = client.post("/article", json={"topic": "topic"})
    assert resp.status_code == 200
    assert resp.json() == {"article": "polished"}


def test_outline_invalid_payload() -> None:
    client = TestClient(fastapi_app.app)
    resp = client.post("/outline", json={})
    assert resp.status_code == 422


def test_article_invalid_payload() -> None:
    client = TestClient(fastapi_app.app)
    resp = client.post("/article", json={})
    assert resp.status_code == 422


def test_query_params(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str | None, str | None]] = []

    class Dummy:
        def build_outline(self, topic: str, ground_truth_url: str = ""):
            return _Doc(f"outline:{topic}")

        def run_pipeline(self, topic: str, ground_truth_url: str = ""):
            return _Doc("article")

    def fake_create_storm(*, output_dir: str | None = None, retriever: str | None = None):
        calls.append((output_dir, retriever))
        return Dummy()

    monkeypatch.setattr(fastapi_app, "_create_storm", fake_create_storm)

    client = TestClient(fastapi_app.app)
    resp = client.post("/outline?output_dir=a&retriever=you", json={"topic": "t"})
    assert resp.status_code == 200
    resp = client.post("/article?output_dir=b&retriever=bing", json={"topic": "t"})
    assert resp.status_code == 200
    assert calls == [("a", "you"), ("b", "bing")]
