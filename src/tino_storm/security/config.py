"""Configuration loading for tino_storm security."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml

CONFIG_PATH = Path.home() / ".tino_storm" / "config.yaml"


def load_config() -> Dict[str, Any]:
    """Load configuration from ``~/.tino_storm/config.yaml`` if it exists."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r") as f:
            data = yaml.safe_load(f) or {}
        return data
    return {}


def get_passphrase() -> str | None:
    """Return the configured passphrase or ``None`` if not configured."""
    cfg = load_config()
    val = cfg.get("passphrase")
    if isinstance(val, str) and val:
        return val
    return None


def encrypt_parquet_enabled() -> bool:
    """Return ``True`` if parquet encryption is enabled in the config."""
    cfg = load_config()
    return bool(cfg.get("encrypt_parquet"))
