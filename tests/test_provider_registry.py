import tino_storm
from tino_storm.providers import Provider, provider_registry


class SampleProvider(Provider):
    def search_sync(
        self,
        query,
        vaults,
        *,
        k_per_vault=5,
        rrf_k=60,
        chroma_path=None,
        vault=None,
    ):
        return [{"url": "custom", "snippets": ["ok"], "meta": {}}]


def setup_function(_):
    provider_registry.clear()


def teardown_function(_):
    provider_registry.clear()


def test_registry_retrieves_and_searches_with_custom_provider():
    provider_registry.register("sample", SampleProvider)
    provider = provider_registry.get("sample")
    assert isinstance(provider, SampleProvider)

    results = tino_storm.search("query", [], provider="sample")
    assert results == [{"url": "custom", "snippets": ["ok"], "meta": {}}]
