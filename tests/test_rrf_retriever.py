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


class DummyRecencyA:
    def forward(self, query, exclude_urls=None):
        return [
            {"url": "a", "recency_rank": 1},
            {"url": "b", "recency_rank": 0},
        ]


class DummyRecencyB:
    def forward(self, query, exclude_urls=None):
        return [
            {"url": "b", "recency_rank": 0},
            {"url": "a", "recency_rank": 1},
        ]


class DummyAuthorityA:
    def forward(self, query, exclude_urls=None):
        return [
            {"url": "a", "authority_rank": 1},
            {"url": "b", "authority_rank": 0},
        ]


class DummyAuthorityB:
    def forward(self, query, exclude_urls=None):
        return [
            {"url": "b", "authority_rank": 0},
            {"url": "a", "authority_rank": 1},
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


def test_rrf_recency_rank_tiebreak():
    retriever = RRFRetriever([DummyRecencyA(), DummyRecencyB()], k=0)
    results = retriever.forward("test")
    urls = [r["url"] for r in results]
    assert urls[:2] == ["b", "a"]


def test_rrf_authority_rank_tiebreak():
    retriever = RRFRetriever([DummyAuthorityA(), DummyAuthorityB()], k=0)
    results = retriever.forward("test")
    urls = [r["url"] for r in results]
    assert urls[:2] == ["b", "a"]
