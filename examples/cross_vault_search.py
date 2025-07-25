"""Example of searching across multiple STORM vaults."""

from tino_storm.ingest import search_vaults


def main() -> None:
    results = search_vaults("climate change", ["science", "news"])
    for item in results:
        snippet = item.get("snippets", [""])[0]
        print(f"{item['url']}: {snippet[:80]}")


if __name__ == "__main__":
    main()
