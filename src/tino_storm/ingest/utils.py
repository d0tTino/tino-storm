"""Shared ingestion utilities."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def list_vaults(root: Optional[str] = None) -> list[str]:
    """Return available vault directories under ``root``.

    If ``root`` is not provided, the ``STORM_VAULT_ROOT`` environment variable is
    consulted. If that is unset, the default ``~/.tino_storm/research`` directory
    is used. Only sub-directories are returned and the result is sorted
    alphabetically.
    """

    root_path = Path(
        root
        or os.environ.get("STORM_VAULT_ROOT")
        or Path.home() / ".tino_storm" / "research"
    ).expanduser()

    if not root_path.exists():
        return []

    return sorted(p.name for p in root_path.iterdir() if p.is_dir())


__all__ = ["list_vaults"]
