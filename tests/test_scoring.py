import tino_storm.retrieval as r
from datetime import datetime, timedelta, timezone


def test_compute_score_recency():
    now = datetime.now(timezone.utc)
    recent = {"meta": {"date": now.isoformat()}}
    older = {"meta": {"date": (now - timedelta(days=10)).isoformat()}}
    assert r.compute_score(recent) > r.compute_score(older)


def test_compute_score_citation_and_confidence():
    base = {"meta": {"citations": 1}}
    confident = {"meta": {"citations": 1, "confidence": 1}}
    assert r.compute_score(confident) > r.compute_score(base)


def test_score_results_sorting():
    now = datetime.now(timezone.utc)
    docs = [
        {"url": "a", "meta": {"date": now.isoformat(), "citations": 1}},
        {"url": "b", "meta": {"date": (now - timedelta(days=5)).isoformat()}},
    ]
    ranked = r.score_results(docs)
    assert ranked[0]["url"] == "a"
