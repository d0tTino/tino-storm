import os
import sys
import numpy as np
import types

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from tino_storm.collaborative_storm.modules.information_insertion_module import (  # noqa: E402
    InsertInformationModule,
)


class DummyEncoder:
    def __init__(self):
        self.vec = np.array([1.0, 0.0])

    def encode(self, text):
        return self.vec


class DummyPredict:
    def __init__(self, res):
        self._res = res

    def __call__(self, *a, **k):
        return types.SimpleNamespace(decision=self._res)


def test_get_sorted_embed_sim_section():
    enc = DummyEncoder()
    mod = InsertInformationModule(engine=None, encoder=enc)
    encoded = np.array([[0.5, 0.5], [1.0, 0.0], [0.0, 1.0]])
    outlines = ["A", "B", "C"]
    enc.vec = np.array([1.0, 0.0])
    res = mod._get_sorted_embed_sim_section(encoded, outlines, "q", "query")
    assert list(res) == ["B", "A", "C"]


def test_choose_candidate_from_embedding_ranking(monkeypatch):
    enc = DummyEncoder()
    mod = InsertInformationModule(engine=None, encoder=enc)
    mod.candidate_choosing = DummyPredict("Best placement: [1]")
    encoded = np.array([[1.0, 0.0], [0.0, 1.0]])
    outlines = ["A", "B"]
    pred = mod.choose_candidate_from_embedding_ranking(
        question="q",
        query="query",
        encoded_outlines=encoded,
        outlines=outlines,
        top_N_candidates=2,
    )
    assert pred.information_placement == "A"
