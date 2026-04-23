import importlib
import inspect
import tomllib
from pathlib import Path

import pytest



def test_adapter_call_uses_search_sync_without_running_loop(monkeypatch):
    cascadence = importlib.import_module("tino_storm.cascadence")
    calls = {}

    def fake_search_sync(query, vaults=None, **kwargs):
        calls["query"] = query
        calls["vaults"] = vaults
        calls["kwargs"] = kwargs
        return ["sync-result"]

    def fail_search(*args, **kwargs):
        raise AssertionError("search should not be used when no loop is running")

    monkeypatch.setattr(cascadence, "_search_sync", fake_search_sync)
    monkeypatch.setattr(cascadence, "_search", fail_search)

    result = cascadence.adapter(
        "hello",
        ["vault-a"],
        provider="stub-provider",
        timeout=1.5,
        raise_on_error=True,
    )

    assert result == ["sync-result"]
    assert calls == {
        "query": "hello",
        "vaults": ["vault-a"],
        "kwargs": {
            "k_per_vault": 5,
            "rrf_k": 60,
            "chroma_path": None,
            "vault": None,
            "provider": "stub-provider",
            "timeout": 1.5,
            "raise_on_error": True,
        },
    }


@pytest.mark.parametrize("anyio_backend", ["asyncio"], scope="module")
@pytest.mark.anyio
async def test_adapter_call_returns_awaitable_when_loop_running(
    monkeypatch, anyio_backend
):
    cascadence = importlib.import_module("tino_storm.cascadence")
    calls = {}

    async def fake_search(query, vaults=None, **kwargs):
        calls["query"] = query
        calls["vaults"] = vaults
        calls["kwargs"] = kwargs
        return ["async-result"]

    def fail_search_sync(*args, **kwargs):
        raise AssertionError("search_sync should not be used when a loop is running")

    monkeypatch.setattr(cascadence, "_search", fake_search)
    monkeypatch.setattr(cascadence, "_search_sync", fail_search_sync)

    awaitable = cascadence.adapter(
        "hello-async",
        ["vault-b"],
        provider="async-provider",
        timeout=2.0,
        raise_on_error=False,
    )

    assert inspect.isawaitable(awaitable)
    assert await awaitable == ["async-result"]
    assert calls == {
        "query": "hello-async",
        "vaults": ["vault-b"],
        "kwargs": {
            "k_per_vault": 5,
            "rrf_k": 60,
            "chroma_path": None,
            "vault": None,
            "provider": "async-provider",
            "timeout": 2.0,
            "raise_on_error": False,
        },
    }


@pytest.mark.parametrize("anyio_backend", ["asyncio"], scope="module")
@pytest.mark.anyio
async def test_adapter_search_passes_through_key_kwargs(monkeypatch, anyio_backend):
    cascadence = importlib.import_module("tino_storm.cascadence")
    calls = {}

    async def fake_search(query, vaults=None, **kwargs):
        calls["query"] = query
        calls["vaults"] = vaults
        calls["kwargs"] = kwargs
        return ["ok"]

    monkeypatch.setattr(cascadence, "_search", fake_search)

    result = await cascadence.adapter.search(
        "query",
        ["vault-c"],
        provider="p",
        timeout=3.25,
        raise_on_error=True,
    )

    assert result == ["ok"]
    assert calls["kwargs"]["provider"] == "p"
    assert calls["kwargs"]["timeout"] == 3.25
    assert calls["kwargs"]["raise_on_error"] is True



def test_adapter_search_sync_passes_through_key_kwargs(monkeypatch):
    cascadence = importlib.import_module("tino_storm.cascadence")
    calls = {}

    def fake_search_sync(query, vaults=None, **kwargs):
        calls["query"] = query
        calls["vaults"] = vaults
        calls["kwargs"] = kwargs
        return ["ok-sync"]

    monkeypatch.setattr(cascadence, "_search_sync", fake_search_sync)

    result = cascadence.adapter.search_sync(
        "query-sync",
        ["vault-d"],
        provider="p-sync",
        timeout=4.5,
        raise_on_error=False,
    )

    assert result == ["ok-sync"]
    assert calls["kwargs"]["provider"] == "p-sync"
    assert calls["kwargs"]["timeout"] == 4.5
    assert calls["kwargs"]["raise_on_error"] is False



def test_task_cascadence_entry_point_is_valid():
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))

    entry = data["project"]["entry-points"]["task_cascadence.integrations"][
        "tino_storm"
    ]
    module_name, attr_name = entry.split(":", 1)

    module = importlib.import_module(module_name)
    exported = getattr(module, attr_name)

    assert entry == "tino_storm.cascadence:adapter"
    assert exported is module.adapter
