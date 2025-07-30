import sys
import types
import pytest

from tino_storm.providers import Provider, load_provider


def test_load_provider_requires_subclass():
    mod = types.ModuleType("dummy_provider")

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
            return []

    class NotAProvider:
        pass

    DummyProvider.__module__ = "dummy_provider"
    NotAProvider.__module__ = "dummy_provider"
    mod.DummyProvider = DummyProvider
    mod.NotAProvider = NotAProvider
    sys.modules["dummy_provider"] = mod

    provider = load_provider("dummy_provider.DummyProvider")
    assert isinstance(provider, DummyProvider)

    with pytest.raises(
        TypeError, match="dummy_provider.NotAProvider is not a Provider"
    ):
        load_provider("dummy_provider.NotAProvider")
