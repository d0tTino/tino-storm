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


def test_score_results_order_and_values():
    now = datetime.now(timezone.utc)
    docs = [
        {
            "url": "a",
            "meta": {
                "date": now.isoformat(),
                "citations": 2,
                "confidence": 0.3,
            },
        },
        {
            "url": "b",
            "meta": {
                "date": (now - timedelta(days=3)).isoformat(),
                "citations": 0,
                "confidence": 0.9,
            },
        },
        {
            "url": "c",
            "meta": {
                "date": (now - timedelta(days=1)).isoformat(),
                "citations": 1,
                "confidence": 0.2,
            },
        },
    ]

    scored = r.score_results(docs)

    def expected_score(doc):
        dt = datetime.fromisoformat(doc["meta"]["date"]).replace(tzinfo=timezone.utc)
        age_days = (now - dt).total_seconds() / 86400
        recency = 1.0 / (1.0 + max(age_days, 0.0))
        return (
            recency
            + doc["meta"].get("citations", 0)
            + doc["meta"].get("confidence", 0.0)
        )

    expected_scores = {d["url"]: expected_score(d) for d in docs}

    # verify ordering by score
    expected_order = [
        u for u, _ in sorted(expected_scores.items(), key=lambda x: x[1], reverse=True)
    ]
    assert [d["url"] for d in scored] == expected_order

    # verify score calculations approximately match expectation
    for item in scored:
        assert abs(item["score"] - expected_scores[item["url"]]) < 0.01
