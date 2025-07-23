from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Dict, Any

import dspy


class OutlineSignature(dspy.Signature):
    """Generate a brief outline for the topic."""

    topic = dspy.InputField("topic to research")
    outline = dspy.OutputField("outline")


class DraftSignature(dspy.Signature):
    """Generate a short draft article from the outline."""

    topic = dspy.InputField("topic")
    outline = dspy.InputField("outline")
    draft = dspy.OutputField("draft article")


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


@dataclass
class ResearchResult:
    outline: str
    draft: str


class ResearchSkill:
    """Simple skill that wraps OutlineModule and DraftModule."""

    def __init__(self, cloud_allowed: bool = False):
        if cloud_allowed:
            lm = dspy.LM("gpt-3.5-turbo")
        else:
            lm = dspy.HFModel("google/flan-t5-small")
        self.outline = OutlineModule(engine=lm)
        self.draft = DraftModule(engine=lm)

    def __call__(
        self, topic: str, vault: Optional[Dict[str, Any]] = None
    ) -> ResearchResult:
        outline_pred = self.outline(topic=topic)
        draft_pred = self.draft(topic=topic, outline=outline_pred.outline)
        return ResearchResult(outline=outline_pred.outline, draft=draft_pred.draft)
