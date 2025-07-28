from __future__ import annotations

from typing import Any, Dict, Optional

import dspy
import dspy.teleprompt as teleprompt

from dspy.teleprompt import BootstrapFewShot
from .research_module import ResearchModule, ResearchResult

if not hasattr(dspy, "teleprompt"):
    dspy.teleprompt = teleprompt


class _DummyLM(dspy.LM):
    """Minimal LM used for testing without external dependencies."""

    def __init__(self) -> None:
        super().__init__(model="dummy")

    def basic_request(self, prompt: str, **kwargs):
        return {"choices": [{"text": ""}]}

    def __call__(
        self,
        prompt: str,
        only_completed: bool = True,
        return_sorted: bool = False,
        **kwargs,
    ):
        return self.basic_request(prompt, **kwargs)


class OutlineSignature(dspy.Signature):
    """Generate a brief outline for the topic."""

    topic = dspy.InputField(desc="topic to research")
    outline = dspy.OutputField(desc="outline")


class DraftSignature(dspy.Signature):
    """Generate a short draft article from the outline."""

    topic = dspy.InputField(desc="topic")
    outline = dspy.InputField(desc="outline")
    draft = dspy.OutputField(desc="draft article")


class OutlineModule(dspy.Module):
    """Module that proposes an outline for a research topic."""

    EVAL_SET = [
        dspy.Example(topic="Photosynthesis", outline="# Introduction"),
        dspy.Example(topic="Eiffel Tower", outline="# History"),
    ]

    def __init__(self, engine: Optional[dspy.LM] = None):
        super().__init__()
        self.engine = engine or dspy.LM("gpt-3.5-turbo")
        self.generate = dspy.Predict(OutlineSignature)

    def forward(self, topic: str) -> dspy.Prediction:
        with dspy.settings.context(lm=self.engine):
            return self.generate(topic=topic)


class DraftModule(dspy.Module):
    """Module that expands an outline into a short draft."""

    EVAL_SET = [
        dspy.Example(
            topic="Photosynthesis",
            outline="# Introduction",
            draft="Photosynthesis is the process by which plants convert light...",
        )
    ]

    def __init__(self, engine: Optional[dspy.LM] = None):
        super().__init__()
        self.engine = engine or dspy.LM("gpt-3.5-turbo")
        self.generate = dspy.Predict(DraftSignature)

    def forward(self, topic: str, outline: str) -> dspy.Prediction:
        with dspy.settings.context(lm=self.engine):
            return self.generate(topic=topic, outline=outline)


class ResearchSkill:
    """Simple skill that wraps OutlineModule and DraftModule."""

    DEFAULT_EVAL_SET = OutlineModule.EVAL_SET + DraftModule.EVAL_SET

    def __init__(
        self,
        cloud_allowed: bool = False,
        eval_sets: Optional[Dict[str, list[dspy.Example]]] = None,
    ):
        """Create the skill.

        Parameters
        ----------
        cloud_allowed:
            Whether remote LMs may be used.
        eval_sets:
            Optional mapping of vault names to DSPy ``Example`` lists used for optimization.
        """

        self.cloud_allowed = cloud_allowed
        if cloud_allowed:
            lm = _DummyLM()
        else:
            try:
                lm = dspy.HFModel("google/flan-t5-small")
            except Exception:
                # Fallback to a simple LM to avoid heavy model downloads in tests
                lm = _DummyLM()
        self.outline = OutlineModule(engine=lm)
        self.draft = DraftModule(engine=lm)
        self.module = ResearchModule(self.outline, self.draft)
        self.eval_sets: Dict[str, list[dspy.Example]] = {
            "default": self.DEFAULT_EVAL_SET
        }
        if eval_sets:
            self.eval_sets.update(eval_sets)

    def __call__(
        self, topic: str, vault: Optional[Dict[str, Any]] = None
    ) -> ResearchResult:
        if getattr(self.module, "_compiled", False):
            return self.module(topic=topic)

        outline_pred = self.outline(topic=topic)
        draft_pred = self.draft(topic=topic, outline=outline_pred.outline)
        return ResearchResult(outline=outline_pred.outline, draft=draft_pred.draft)

    def optimize(self, vault: str = "default") -> None:
        """Optimize prompts using DSPy when cloud access is allowed."""

        if not self.cloud_allowed:
            return

        eval_set = self.eval_sets.get(vault, self.DEFAULT_EVAL_SET)
        trainer = BootstrapFewShot()
        trainer.compile(self.module, trainset=eval_set, valset=eval_set)
