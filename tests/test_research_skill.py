# ruff: noqa
import os
import sys
import types

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from knowledge_storm.storm_wiki.modules.knowledge_curation import (  # noqa: E402
    StormKnowledgeCurationModule,
    DialogueTurn,
    StormInformationTable,
)
from knowledge_storm.storm_wiki.modules.callback import (  # noqa: E402
    BaseCallbackHandler,
)  # noqa: E402
from tino_storm.core.interface import Information  # noqa: E402


class DummyRetriever:
    def retrieve(self, queries, exclude_urls=None):
        return [Information(url="u", description="d", snippets=["s"], title="t")]


class DummyPersonaGen:
    def generate_persona(self, topic, max_num_persona=1):
        return ["p1"]


class DummyConv:
    def __init__(self):
        self.dlg_history = [
            DialogueTurn(
                agent_utterance="a",
                user_utterance="q",
                search_queries=["q"],
                search_results=[
                    Information(url="u", description="d", snippets=["s"], title="t")
                ],
            )
        ]


class DummyHandler(BaseCallbackHandler):
    pass


def test_research_skill(monkeypatch):
    mod = StormKnowledgeCurationModule(
        retriever=DummyRetriever(),
        persona_generator=DummyPersonaGen(),
        conv_simulator_lm=None,
        question_asker_lm=None,
        max_search_queries_per_turn=1,
        search_top_k=1,
        max_conv_turn=1,
        max_thread_num=1,
    )
    mod.conv_simulator = lambda **kw: types.SimpleNamespace(
        dlg_history=DummyConv().dlg_history
    )
    table = mod.research(
        topic="topic",
        ground_truth_url="",
        callback_handler=DummyHandler(),
        disable_perspective=True,
    )
    assert isinstance(table, StormInformationTable)
    assert "u" in table.url_to_info
