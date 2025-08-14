from types import SimpleNamespace

from tino_storm.providers import Provider
from tino_storm.providers.registry import ProviderRegistry


class DummyProvider(Provider):
    async def search_async(self, query, vaults, **kwargs):  # pragma: no cover - simple stub
        return []

    def search_sync(self, query, vaults, **kwargs):  # pragma: no cover - simple stub
        return []


def test_loads_providers_from_entry_points(monkeypatch):
    dummy_ep = SimpleNamespace(name="dummy", load=lambda: DummyProvider)

    def fake_entry_points(*, group):
        assert group == "tino_storm.providers"
        return [dummy_ep]

    monkeypatch.setattr(
        "tino_storm.providers.registry.entry_points", fake_entry_points
    )
    registry = ProviderRegistry()
    assert isinstance(registry.get("dummy"), DummyProvider)
