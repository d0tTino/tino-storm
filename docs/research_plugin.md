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
