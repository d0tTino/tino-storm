import asyncio

import pytest

from tino_storm.providers.docs_hub_client import DocsHubClient


class DummyResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self):
        return []


class DummyClient:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, *args, **kwargs):
        return DummyResponse()


class DummyAsyncResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self):
        return []


class DummyAsyncClient:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        return DummyAsyncResponse()


@pytest.fixture
def docs_hub_client():
    return DocsHubClient(base_url="https://docs.example", timeout=3.0)


def test_search_uses_call_timeout(monkeypatch, docs_hub_client):
    captured = {}

    def fake_client(**kwargs):
        captured.update(kwargs)
        return DummyClient(**kwargs)

    monkeypatch.setattr("httpx.Client", fake_client)

    docs_hub_client.search(
        "query",
        ["vault"],
        k_per_vault=1,
        rrf_k=10,
        chroma_path=None,
        vault=None,
        timeout=1.5,
    )

    assert captured["timeout"] == 1.5


def test_search_falls_back_to_default_timeout(monkeypatch, docs_hub_client):
    captured = {}

    def fake_client(**kwargs):
        captured.update(kwargs)
        return DummyClient(**kwargs)

    monkeypatch.setattr("httpx.Client", fake_client)

    docs_hub_client.search(
        "query",
        ["vault"],
        k_per_vault=1,
        rrf_k=10,
        chroma_path=None,
        vault=None,
        timeout=None,
    )

    assert captured["timeout"] == 3.0


def test_search_async_uses_call_timeout(monkeypatch, docs_hub_client):
    captured = {}

    def fake_client(**kwargs):
        captured.update(kwargs)
        return DummyAsyncClient(**kwargs)

    monkeypatch.setattr("httpx.AsyncClient", fake_client)

    async def run():
        await docs_hub_client.search_async(
            "query",
            ["vault"],
            k_per_vault=1,
            rrf_k=10,
            chroma_path=None,
            vault=None,
            timeout=2.5,
        )

    asyncio.run(run())

    assert captured["timeout"] == 2.5
