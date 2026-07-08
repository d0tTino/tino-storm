import importlib
import sys

import pytest


@pytest.fixture
def _restore_module_cache():
    original_modules = sys.modules.copy()
    yield
    for name in list(sys.modules):
        if name not in original_modules:
            sys.modules.pop(name)


def _simulate_missing(monkeypatch, prefix: str) -> None:
    for name in list(sys.modules):
        if name == prefix or name.startswith(prefix + "."):
            monkeypatch.delitem(sys.modules, name, raising=False)

    real_find_spec = importlib.util.find_spec

    def fake_find_spec(name, *args, **kwargs):
        if name == prefix or name.startswith(prefix + "."):
            return None
        return real_find_spec(name, *args, **kwargs)

    real_import_module = importlib.import_module

    def fake_import_module(name, package=None):
        if name == prefix or name.startswith(prefix + "."):
            raise ModuleNotFoundError(name=prefix)
        return real_import_module(name, package)

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)
    monkeypatch.setattr(importlib, "import_module", fake_import_module)


def test_provider_base_import_does_not_import_bing_search():
    module = importlib.import_module("tino_storm.providers.base")

    assert module.DefaultProvider is not None
    assert "tino_storm.core.rm" not in sys.modules


def test_tino_search_imports_without_bing_llm_extras(
    monkeypatch, _restore_module_cache
):
    for dependency in ("dspy", "backoff", "dsp"):
        _simulate_missing(monkeypatch, dependency)

    module = importlib.import_module("tino_storm.search")

    assert module.search_sync is not None


def test_default_provider_bing_falls_back_without_llm_extras(
    monkeypatch, _restore_module_cache, caplog
):
    for dependency in ("dspy", "backoff", "dsp"):
        _simulate_missing(monkeypatch, dependency)
    monkeypatch.setenv("BING_SEARCH_API_KEY", "test-key")

    from tino_storm.providers.base import DefaultProvider

    results = DefaultProvider()._bing_search("query")

    assert results == []
    assert "Bing search dependencies are unavailable" in caplog.text
