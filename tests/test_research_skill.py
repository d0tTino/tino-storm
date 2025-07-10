import dspy
from tino_storm.dsp import ResearchSkill


class StubLM(dspy.LM):
    """Simple LM that always returns a preset response."""

    def __init__(self, response: str):
        super().__init__(model="stub")
        self.response = response

    def basic_request(self, prompt, **kwargs):
        return self.response


class StubOutlineModule:
    def __init__(self, resp="outline"):
        self.resp = resp

    def generate_outline(self, topic, information_table, callback_handler=None):
        return self.resp


class StubDraftModule:
    def __init__(self, resp="draft"):
        self.resp = resp

    def generate_article(
        self, topic, information_table, article_with_outline, callback_handler=None
    ):
        return self.resp


class StubPolishModule:
    def __init__(self, resp="polished"):
        self.resp = resp

    def polish_article(self, topic, draft_article, remove_duplicate=False):
        return self.resp


def test_research_skill_runs_with_stubs():
    skill = ResearchSkill(
        outline_module=StubOutlineModule("o"),
        draft_module=StubDraftModule("d"),
        polish_module=StubPolishModule("p"),
    )

    result = skill("topic", None)
    assert result == "p"
