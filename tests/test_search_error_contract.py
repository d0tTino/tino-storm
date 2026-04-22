import asyncio

import pytest

from tino_storm.search import ResearchError, SearchResults, search_async, search_sync


class _FailingProvider:
    def search_sync(self, query, vaults, **kwargs):
        raise RuntimeError("boom")

    async def search_async(self, query, vaults, **kwargs):
        raise RuntimeError("boom")


def test_search_sync_default_soft_fail_contract():
    results = search_sync("topic", ["vault"], provider=_FailingProvider())

    assert isinstance(results, SearchResults)
    assert results == []
    assert len(results.errors) == 1
    error = results.errors[0]
    assert error["error"] == "boom"
    assert error["provider"] == "_FailingProvider"
    assert error["exception_type"] == "RuntimeError"
    assert error["query"] == "topic"


def test_search_sync_raise_on_error_contract():
    with pytest.raises(ResearchError, match="boom"):
        search_sync(
            "topic",
            ["vault"],
            provider=_FailingProvider(),
            raise_on_error=True,
        )


def test_search_async_default_soft_fail_contract():
    async def _run():
        return await search_async("topic", ["vault"], provider=_FailingProvider())

    results = asyncio.run(_run())

    assert isinstance(results, SearchResults)
    assert results == []
    assert len(results.errors) == 1
    error = results.errors[0]
    assert error["error"] == "boom"
    assert error["provider"] == "_FailingProvider"
    assert error["exception_type"] == "RuntimeError"
    assert error["query"] == "topic"


def test_search_async_raise_on_error_contract():
    async def _run():
        return await search_async(
            "topic",
            ["vault"],
            provider=_FailingProvider(),
            raise_on_error=True,
        )

    with pytest.raises(ResearchError, match="boom"):
        asyncio.run(_run())
