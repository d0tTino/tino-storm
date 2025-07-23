import sys
import types

# Provide a minimal dspy.teleprompt stub if missing
if "dspy.teleprompt" not in sys.modules:
    tp = types.ModuleType("dspy.teleprompt")

    class BootstrapFewShot:
        def compile(self, student, *, trainset, valset=None, teacher=None):
            return student

    tp.BootstrapFewShot = BootstrapFewShot
    sys.modules["dspy.teleprompt"] = tp

import dspy

if not hasattr(dspy, "Example"):

    class Example:
        def __init__(self, *a, **k):
            pass

    class Signature:
        pass

    class InputField:
        def __init__(self, *a, **k):
            pass

    class OutputField:
        def __init__(self, *a, **k):
            pass

    class Predict:
        def __init__(self, *a, **k):
            pass

        def __call__(self, *a, **k):
            return types.SimpleNamespace()

    class Module:
        def __init__(self, *a, **k):
            pass

        def __call__(self, *a, **k):
            return self.forward(*a, **k)

    class LM:
        def __init__(self, *a, **k):
            pass

    class HFModel:
        def __init__(self, *a, **k):
            pass

    dspy.Example = Example
    dspy.Signature = Signature
    dspy.InputField = InputField
    dspy.OutputField = OutputField
    dspy.Predict = Predict
    dspy.Module = Module
    dspy.LM = LM
    dspy.HFModel = HFModel
    dspy.teleprompt = types.ModuleType("teleprompt")
    dspy.teleprompt.BootstrapFewShot = BootstrapFewShot

from tino_storm.skills.research import ResearchSkill


class DummyPredict:
    def __init__(self, value):
        self._value = value

    def __call__(self, *a, **k):
        return types.SimpleNamespace(**self._value)


def test_research_skill_call(monkeypatch):
    skill = ResearchSkill(cloud_allowed=False)
    monkeypatch.setattr(
        skill.outline, "forward", lambda *a, **k: types.SimpleNamespace(outline="o")
    )
    monkeypatch.setattr(
        skill.draft,
        "forward",
        lambda *a, **k: types.SimpleNamespace(draft="d"),
    )
    result = skill("topic")
    assert result.outline == "o"
    assert result.draft == "d"


def test_optimize_runs(monkeypatch):
    skill = ResearchSkill(cloud_allowed=True)

    def dummy_compile(self, student, *, trainset, valset=None, teacher=None):
        dummy_compile.called = True
        return student

    dummy_compile.called = False
    monkeypatch.setattr(dspy.teleprompt.BootstrapFewShot, "compile", dummy_compile)
    skill.optimize()
    assert dummy_compile.called
