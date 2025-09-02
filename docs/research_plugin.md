# Using Tino Storm as a research plugin

`tino_storm.search()` and `tino_storm.search_async()` can be embedded in
language-model agents to query one or more STORM vaults. Install optional
extras to pull in additional features:

```bash
pip install tino-storm[research]  # FastAPI server and filesystem watcher
pip install tino-storm[scrapers]  # ingestion helpers for social platforms
pip install tino-storm[retrieval] # semantic search and vector DB helpers
```

The synchronous helper automatically delegates to `search_async()` when an event
loop is active.

```python
import asyncio
import tino_storm

async def main():
    results = await tino_storm.search("large language models", ["science"])
    print(results)

asyncio.run(main())
```

The search API returns a list of `ResearchResult` objects containing the URL,
text snippets, optional metadata and a short summary from the retrieved
documents. By default the first snippet is used as the summary. If the
`STORM_SUMMARY_MODEL` environment variable is set, that model will be invoked
to generate a one-sentence summary for each result. The optional
`STORM_SUMMARY_TIMEOUT` variable limits how long the summarizer is allowed to
run before the first snippet is used as a fallback.

```python
from tino_storm.search_result import ResearchResult

result = ResearchResult(url="https://example.com", snippets=["excerpt"], meta={})
```

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

### Async providers

Providers may implement an asynchronous ``search_async`` method. For example,
``BingAsyncProvider`` uses ``httpx`` to perform non-blocking web searches.

```python
from tino_storm.providers.bing_async import BingAsyncProvider

results = await BingAsyncProvider().search_async("large language models", ["science"])
```

### Entry-point discovery

Third-party packages can expose providers through the
``tino_storm.providers`` entry-point group so they are discovered at import
time:

```toml
# pyproject.toml
[project.entry-points."tino_storm.providers"]
"my-provider" = "my_package.providers:MyProvider"
```

Once installed, such providers are available by name via ``provider_registry``
or the ``provider`` argument to ``search`` and ``search_async``.

## Custom provider lists

Multiple providers can be combined by passing a comma-separated list to the
``provider`` argument or the ``STORM_SEARCH_PROVIDER`` environment variable. The
list is resolved into a ``ProviderAggregator`` which queries each provider and
merges their results.

```python
results = await tino_storm.search_async(
    "large language models",
    provider="default,my-provider",
)
```

## Error handling

When a provider fails to complete a query, ``search`` and ``search_async``
raise ``ResearchError``. Catch this exception to handle failures gracefully.

```python
from tino_storm.search import ResearchError, search

try:
    search("large language models", provider="failing-provider")
except ResearchError as e:
    print("Search failed:", e)
```

## Async API usage

The FastAPI app backing Tino Storm can be exercised from asynchronous code
using ``httpx.AsyncClient``. Mount the app and await endpoint calls to issue
requests without blocking the event loop.

```python
import asyncio
from httpx import AsyncClient
from tino_storm.api import app as api_app

async def run():
    async with AsyncClient(app=api_app, base_url="http://test") as app:
        resp = await app.post(
            "/search",
            json={"query": "large language models", "vaults": ["science"]},
        )
        print(resp.json())

asyncio.run(run())
```

## Event hooks

Tino Storm exposes an ``event_emitter`` for reacting to research-related
events. Subscribe to ``ResearchAdded`` to receive notifications when research
is ingested or when searches emit error events.

```python
from tino_storm.events import event_emitter, ResearchAdded

async def on_research(event: ResearchAdded):
    print("Research event:", event.topic, event.information_table)

event_emitter.subscribe(ResearchAdded, on_research)
```

For synchronous code paths, use ``event_emitter.emit_sync`` to dispatch the
same events. Any asynchronous handlers are executed on a temporary event loop
so they do not block the caller.

```python
from tino_storm.events import event_emitter, ResearchAdded

def on_research_sync(event: ResearchAdded):
    print("Research event:", event.topic)

event_emitter.subscribe(ResearchAdded, on_research_sync)

event_emitter.emit_sync(ResearchAdded(topic="ai", information_table={}))
```
