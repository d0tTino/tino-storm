# Ingestion folder layout

`tino-storm ingest` monitors a directory for dropped files. The specified `--root` acts as the vault root where each first level subdirectory becomes a vault name.

Example structure:

```text
vault-root/
  science/
    notes.txt
    links.urls
  news/
    manifest.web
    papers.arxiv
```

Dropped files are routed to the vault named after their immediate parent directory and stored in a Chroma database under `~/.tino_storm/chroma` (change with `STORM_CHROMA_PATH`).

## Supported manifest types

The watcher recognises several file extensions and processes them via the ingestion scrapers:

- `.url` or `.urls` – newline separated list of URLs
- `.web` – JSON array of URLs crawled by [`crawler.py`](../src/tino_storm/ingestion/crawler.py)
- `.twitter` – search query handled by [`twitter.py`](../src/tino_storm/ingestion/twitter.py)
- `.reddit` – first line subreddit, optional second line query, scraped by [`reddit.py`](../src/tino_storm/ingestion/reddit.py)
- `.arxiv` – one arXiv identifier per line fetched by [`arxiv.py`](../src/tino_storm/ingestion/arxiv.py)
- `.4chan` – board name and thread number ingested via [`fourchan.py`](../src/tino_storm/ingestion/fourchan.py)

Any other text file is added to the vault verbatim.

## Plain text files

Plain `.txt` files can be dropped directly into any vault folder. They are read
by `llama_index`'s `SimpleDirectoryReader`, which loads each file as a single
document while capturing file metadata such as the path and timestamps. The
resulting document is then ingested into the Chroma collection under the vault
name.
