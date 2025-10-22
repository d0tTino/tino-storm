# Testing Guidelines

The API helpers and ingestion flows rely on background threads and event
emission. When making changes in these areas, run the focused pytest module to
ensure the concurrency and error-handling behaviour stays intact:

```bash
pytest tests/test_api_endpoints.py
```

This suite includes checks for `run_research` vault ingestion success/failure,
asynchronous `/research` and `/ingest` endpoint error propagation, and event
emission coverage. Running the full module is preferred because it exercises
the mocked FastAPI client helpers shared across the tests.

If you are iterating on a specific scenario you can narrow the run with `-k`,
for example:

```bash
pytest tests/test_api_endpoints.py -k run_research_ingestion
```

These commands do not require external services thanks to the mocked
`STORMWikiRunner` and `VaultIngestHandler` implementations used by the tests.
