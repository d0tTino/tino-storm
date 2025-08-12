from __future__ import annotations

from typing import Dict, Type

from .base import Provider


class ProviderRegistry:
    """Registry mapping names to provider classes."""

    def __init__(self) -> None:
        self._providers: Dict[str, Type[Provider]] = {}

    def register(self, name: str, provider_cls: Type[Provider]) -> None:
        """Register a provider class under ``name``."""
        if not issubclass(provider_cls, Provider):
            raise TypeError("provider_cls must subclass Provider")
        self._providers[name] = provider_cls

    def get(self, name: str) -> Provider:
        """Return an instance of the provider registered under ``name``."""
        cls = self._providers[name]
        return cls()

    def clear(self) -> None:
        """Remove all registered providers."""
        self._providers.clear()


provider_registry = ProviderRegistry()

__all__ = ["ProviderRegistry", "provider_registry"]
