from __future__ import annotations

import asyncio
from typing import Dict, Iterable, Union


from .base import Provider


class ProviderRegistry:
    """Registry mapping names to provider instances."""

    def __init__(self) -> None:
        self._providers: Dict[str, Provider] = {}

    def register(
        self, name: str, provider: Union[Provider, type[Provider]]
    ) -> Provider:
        """Register *provider* under *name*.

        ``provider`` may be a Provider instance or subclass; subclasses are
        instantiated with no arguments.
        """

        if isinstance(provider, type):
            provider = provider()  # type: ignore[call-arg]
        self._providers[name] = provider
        return provider

    def get(self, name: str) -> Provider:
        """Return the provider registered under *name*."""

        return self._providers[name]

    def compose(self, *names: str) -> Provider:
        """Compose multiple providers into a single provider.

        The returned provider queries all composed providers and merges their
        results.
        """

        providers = [self.get(n) for n in names]

        class _Composite(Provider):
            def __init__(self, providers: Iterable[Provider]):
                self.providers = list(providers)

            async def search_async(self, query: str, vaults: Iterable[str], **kwargs):
                results = await asyncio.gather(
                    *[p.search_async(query, vaults, **kwargs) for p in self.providers]
                )
                merged = []
                for r in results:
                    merged.extend(r)
                return merged

            def search_sync(self, query: str, vaults: Iterable[str], **kwargs):
                merged = []
                for p in self.providers:
                    merged.extend(p.search_sync(query, vaults, **kwargs))
                return merged

        return _Composite(providers)

    def available(self) -> Dict[str, Provider]:
        """Return a copy of the registered providers mapping."""

        return dict(self._providers)



provider_registry = ProviderRegistry()


def register_provider(name: str):
    """Decorator to register a provider class under *name*."""

    def decorator(cls: Union[type[Provider], Provider]):
        provider_registry.register(name, cls)
        return cls

    return decorator

