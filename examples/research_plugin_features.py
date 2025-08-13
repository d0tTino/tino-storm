"""Demonstrate custom providers, ResearchError and async event hooks."""

import asyncio

from tino_storm.events import ResearchAdded, event_emitter
from tino_storm.providers import Provider, register_provider
from tino_storm.search import ResearchError, search_async


@register_provider("failing-provider")
class FailingProvider(Provider):
    async def search_async(self, query, vaults, **kwargs):
        raise RuntimeError("boom")


def handle_research(event: ResearchAdded):
    print("Research event:", event.topic, event.information_table)


event_emitter.subscribe(ResearchAdded, handle_research)


async def main() -> None:
    try:
        await search_async("large language models", provider="default,failing-provider")
    except ResearchError as exc:
        print("Search failed:", exc)


if __name__ == "__main__":
    asyncio.run(main())
