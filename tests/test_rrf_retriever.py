from tino_storm.rrf import RRFRetriever


class DummyA:
    def forward(self, query, exclude_urls=None):
        return [
            {"url": "a", "title": "A"},
            {"url": "b", "title": "B"},
        ]


class DummyB:
    def forward(self, query, exclude_urls=None):
        return [
            {"url": "b", "title": "B"},
            {"url": "c", "title": "C"},
        ]


def test_rrf_ranking_order():
    retriever = RRFRetriever([DummyA(), DummyB()], k=0)
    results = retriever.forward("test")
    urls = [r["url"] for r in results]
    assert urls == ["b", "a", "c"]


def test_rrf_exclude_urls():
    retriever = RRFRetriever([DummyA(), DummyB()], k=0)
    results = retriever.forward("test", exclude_urls=["b"])
    urls = [r["url"] for r in results]
    assert urls == ["a", "c"]


def test_rrf_exclude_urls_iterable_equivalence():
    retriever = RRFRetriever([DummyA(), DummyB()], k=0)
    results_list = retriever.forward("test", exclude_urls=["b"])
    results_set = retriever.forward("test", exclude_urls={"b"})
    assert results_list == results_set
