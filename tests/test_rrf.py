import tino_storm.retrieval as r


def test_rrf_ordering():
    recency = [{"url": "a"}, {"url": "b"}, {"url": "c"}]
    authority = [{"url": "b"}, {"url": "a"}, {"url": "c"}]
    similarity = [{"url": "a"}, {"url": "c"}, {"url": "b"}]
    result = r.combine_ranks(recency, authority, similarity, k=60)
    assert [d["url"] for d in result] == ["a", "b", "c"]
