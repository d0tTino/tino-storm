# VectorDBProvider

The `VectorDBProvider` allows Tino Storm to query external vector databases
using an existing retrieval helper such as `VectorRM`.

## Usage

```python
from tino_storm.providers import VectorDBProvider
from tino_storm.rm import VectorRM

# Configure the retrieval model (e.g., connect to Qdrant)
rm = VectorRM(collection_name="docs", embedding_model="BAAI/bge-m3")
rm.init_offline_vector_db(vector_store_path="/path/to/store")

provider = VectorDBProvider(rm)
results = provider.search_sync("example query", vaults=[])
```

The provider expects the retriever to expose a `forward` method returning
results in the standard search format:

```python
[{"url": "https://example.com", "snippets": ["..."], "meta": {...}}]
```

Errors during retrieval are reported via the `ResearchAdded` event with the
error message included in the information table.
