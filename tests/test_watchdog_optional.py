"""Tests around optional watchdog dependency for search entrypoints."""

from __future__ import annotations

import asyncio
import importlib
import sys
from collections.abc import Iterable


def _pop_modules(prefixes: Iterable[str]) -> dict[str, object]:
    """Remove matching modules from ``sys.modules`` and return the originals."""

    removed: dict[str, object] = {}
    for name in list(sys.modules):
        if any(name == prefix or name.startswith(f"{prefix}.") for prefix in prefixes):
            module = sys.modules.pop(name, None)
            if module is not None:
                removed[name] = module
    return removed


def test_search_succeeds_without_watchdog(monkeypatch, tmp_path):
    """``tino_storm.search`` should not require watchdog to be importable."""

    monkeypatch.setenv("STORM_VAULT_ROOT", str(tmp_path))
    monkeypatch.delenv("BING_SEARCH_API_KEY", raising=False)

    removed_watchdog = _pop_modules(["watchdog"])
    removed_tino = _pop_modules(["tino_storm"])

    try:
        tino_storm = importlib.import_module("tino_storm")
        results = asyncio.run(tino_storm.search("optional dependency", vaults=[]))
        assert results == []
    finally:
        # Remove modules imported during this test before restoring originals.
        _pop_modules(["tino_storm", "watchdog"])
        for name, module in removed_tino.items():
            sys.modules[name] = module
        for name, module in removed_watchdog.items():
            sys.modules[name] = module
