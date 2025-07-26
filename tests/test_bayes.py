import tino_storm.retrieval as r
from datetime import datetime, timedelta, timezone


def test_posterior_decreases_with_age():
    now = datetime.now(timezone.utc)
    recent = {"meta": {"date": now.isoformat(), "citations": 0}}
    old = {"meta": {"date": (now - timedelta(days=5)).isoformat(), "citations": 0}}
    assert r.update_posterior(recent, prior=0.5) > r.update_posterior(old, prior=0.5)


def test_posterior_increases_with_citations():
    now = datetime.now(timezone.utc)
    low = {"meta": {"date": now.isoformat(), "citations": 1}}
    high = {"meta": {"date": now.isoformat(), "citations": 5}}
    assert r.update_posterior(high, prior=0.5) > r.update_posterior(low, prior=0.5)
