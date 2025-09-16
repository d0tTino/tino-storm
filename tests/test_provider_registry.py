import tino_storm
from tino_storm.providers import Provider, provider_registry
from tino_storm.search_result import ResearchResult


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
        timeout=None,
    ) -> list[ResearchResult]:
        return [ResearchResult(url="custom", snippets=["ok"], meta={})]


def setup_function(_):
    provider_registry.clear()


def teardown_function(_):
    provider_registry.clear()


def test_registry_retrieves_and_searches_with_custom_provider():
    provider_registry.register("sample", SampleProvider)
    provider = provider_registry.get("sample")
    assert isinstance(provider, SampleProvider)

    results = tino_storm.search_sync("query", [], provider="sample")
    assert results == [ResearchResult(url="custom", snippets=["ok"], meta={})]
