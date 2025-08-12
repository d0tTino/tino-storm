# Using Tino Storm as a research plugin

`tino_storm.search()` and `tino_storm.search_async()` can be embedded in language-model agents to query one or more STORM vaults. The synchronous helper automatically delegates to `search_async()` when an event loop is active.

```python
import asyncio
import tino_storm

async def main():
    results = await tino_storm.search("large language models", ["science"])
    print(results)

asyncio.run(main())
```

The search API returns a list of result dictionaries containing the URL, title and text snippets from the retrieved documents.

## Custom search providers

You can plug in your own search provider by setting the `STORM_SEARCH_PROVIDER`
environment variable to the dotted path of a class implementing the
`Provider` interface.

```bash
export STORM_SEARCH_PROVIDER=my_package.providers.MyProvider
```

This provider will be loaded automatically whenever `tino_storm.search()` is
invoked.

### Registering providers programmatically

Providers can also be registered directly in code using the provider
registry. This is useful when you want to compose multiple providers or make
them available under friendly names.

```python
from tino_storm.providers import provider_registry, DefaultProvider

# Register custom provider class or instance under a name
provider_registry.register("default", DefaultProvider)
provider_registry.register("my-provider", MyProvider())

# Compose several providers into one
combined = provider_registry.compose("default", "my-provider")
results = combined.search("large language models", ["science"])
```

The `register_provider` decorator can also be used to register a provider
class:

```python
from tino_storm.providers import register_provider

@register_provider("my-provider")
class MyProvider(Provider):
    ...
```
