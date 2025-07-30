import sys
import types

import pytest

import tino_storm
from tino_storm.providers import Provider, load_provider


def test_load_provider_raises(monkeypatch):
    mod = types.ModuleType("dummy_mod")

    class NotProvider:
        pass

    mod.NotProvider = NotProvider
    monkeypatch.setitem(sys.modules, "dummy_mod", mod)

    with pytest.raises(TypeError):
        load_provider("dummy_mod.NotProvider")


def test_search_uses_env_provider(monkeypatch):
    calls = {}

    class DummyProvider(Provider):
        def search_sync(
            self,
            query,
            vaults,
            *,
            k_per_vault=5,
            rrf_k=60,
            chroma_path=None,
            vault=None,
        ):
            calls["args"] = (
                query,
                list(vaults),
                k_per_vault,
                rrf_k,
                chroma_path,
                vault,
            )
            return ["ok"]

    mod = types.ModuleType("dummy_provider_mod")
    mod.DummyProvider = DummyProvider
    monkeypatch.setitem(sys.modules, "dummy_provider_mod", mod)
    monkeypatch.setenv("STORM_SEARCH_PROVIDER", "dummy_provider_mod.DummyProvider")

    result = tino_storm.search("q", ["v"])

    assert result == ["ok"]
    assert calls["args"] == ("q", ["v"], 5, 60, None, None)
