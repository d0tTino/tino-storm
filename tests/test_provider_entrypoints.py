from types import SimpleNamespace
import logging

from tino_storm.providers import Provider
from tino_storm.providers.registry import ProviderRegistry


class DummyProvider(Provider):
    async def search_async(
        self, query, vaults, **kwargs
    ):  # pragma: no cover - simple stub
        return []

    def search_sync(self, query, vaults, **kwargs):  # pragma: no cover - simple stub
        return []


def test_loads_providers_from_entry_points(monkeypatch):
    dummy_ep = SimpleNamespace(name="dummy", load=lambda: DummyProvider)

    def fake_entry_points(*, group):
        assert group == "tino_storm.providers"
        return [dummy_ep]

    monkeypatch.setattr("tino_storm.providers.registry.entry_points", fake_entry_points)
    registry = ProviderRegistry()
    assert isinstance(registry.get("dummy"), DummyProvider)


def test_logs_warning_for_faulty_entry_point(monkeypatch, caplog):
    def bad_load():
        raise RuntimeError("boom")

    bad_ep = SimpleNamespace(name="bad", load=bad_load)

    def fake_entry_points(*, group):
        assert group == "tino_storm.providers"
        return [bad_ep]

    monkeypatch.setattr("tino_storm.providers.registry.entry_points", fake_entry_points)

    with caplog.at_level(logging.WARNING):
        registry = ProviderRegistry()

    assert "bad" in caplog.text
    assert "boom" in caplog.text
    assert "bad" not in registry.available()
