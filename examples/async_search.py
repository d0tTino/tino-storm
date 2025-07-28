"""Example demonstrating asynchronous search usage."""

import asyncio
import tino_storm


async def main() -> None:
    results = await tino_storm.search("large language models", ["science"])
    for item in results:
        snippet = item.get("snippets", [""])[0]
        print(f"{item['url']}: {snippet[:80]}")


if __name__ == "__main__":
    asyncio.run(main())
