"""Utilities for ingesting external resources into Chroma collections."""

from .watcher import start_watcher, VaultIngestHandler

__all__ = ["start_watcher", "VaultIngestHandler"]
