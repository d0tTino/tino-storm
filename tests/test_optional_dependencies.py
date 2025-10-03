import importlib
import sys

import pytest

from tino_storm._extras import MissingExtraError


@pytest.fixture
def _restore_module_cache():
    """Ensure modified modules are reloaded after each test."""

    original_modules = sys.modules.copy()
    yield
    for name in list(sys.modules):
        if name not in original_modules:
            sys.modules.pop(name)


def _simulate_missing(monkeypatch, prefix: str) -> None:
    """Force optional dependency *prefix* to appear missing."""

    for name in list(sys.modules):
        if name == prefix or name.startswith(prefix + "."):
            monkeypatch.delitem(sys.modules, name, raising=False)

    real_find_spec = importlib.util.find_spec

    def fake_find_spec(name, *args, **kwargs):  # pragma: no cover - passthrough
        if name == prefix or name.startswith(prefix + "."):
            return None
        return real_find_spec(name, *args, **kwargs)

    real_import_module = importlib.import_module

    def fake_import_module(name, package=None):  # pragma: no cover - passthrough
        if name == prefix or name.startswith(prefix + "."):
            raise ModuleNotFoundError(name=prefix)
        return real_import_module(name, package)

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)
    monkeypatch.setattr(importlib, "import_module", fake_import_module)


def test_lm_missing_llm_extra(monkeypatch, _restore_module_cache):
    _simulate_missing(monkeypatch, "litellm")
    monkeypatch.delitem(sys.modules, "tino_storm.lm", raising=False)

    with pytest.raises(MissingExtraError) as excinfo:
        importlib.import_module("tino_storm.lm")

    assert "pip install tino-storm[llm]" in str(excinfo.value)


def test_research_skill_missing_dspy(monkeypatch, _restore_module_cache):
    _simulate_missing(monkeypatch, "dspy")
    for name in [
        "tino_storm",
        "tino_storm.skills",
        "tino_storm.skills.research",
        "tino_storm.skills.research_module",
    ]:
        monkeypatch.delitem(sys.modules, name, raising=False)

    with pytest.raises(MissingExtraError) as excinfo:
        importlib.import_module("tino_storm.skills.research")

    assert "pip install tino-storm[llm]" in str(excinfo.value)
