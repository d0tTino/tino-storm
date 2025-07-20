from tino_storm.config import create_retriever
from tino_storm.rrf import RRFRetriever


def test_create_retriever_rrf(monkeypatch):
    monkeypatch.setenv("BING_SEARCH_API_KEY", "bing")
    monkeypatch.setenv("YDC_API_KEY", "you")
    retriever = create_retriever("rrf=bing,you", 5)
    assert isinstance(retriever, RRFRetriever)
    assert len(retriever.retrievers) == 2
    assert retriever.retrievers[0].__class__.__name__ == "BingSearch"
    assert retriever.retrievers[1].__class__.__name__ == "YouRM"
    assert retriever.top_n == 5
