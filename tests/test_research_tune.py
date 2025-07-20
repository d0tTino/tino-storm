import dspy
from tino_storm.dsp import ResearchSkill, OutlineModule, DraftModule, PolishModule


class TopicLM(dspy.LM):
    def basic_request(self, prompt, **kwargs):
        if "Quantum computing" in prompt:
            return "QC article"
        if "Machine learning" in prompt:
            return "ML article"
        if "Climate change" in prompt:
            return "CC article"
        return "UNKNOWN"


def test_tune_example_vault(tmp_path):
    lm = TopicLM(model="stub")
    skill = ResearchSkill(
        outline_module=OutlineModule(lm),
        draft_module=DraftModule(lm),
        polish_module=PolishModule(lm),
    )
    acc = skill.tune("example_vault")
    assert acc == 1.0


def test_tune_another_vault(tmp_path):
    lm = TopicLM(model="stub")
    skill = ResearchSkill(
        outline_module=OutlineModule(lm),
        draft_module=DraftModule(lm),
        polish_module=PolishModule(lm),
    )
    acc = skill.tune("another_vault")
    assert acc == 1.0
