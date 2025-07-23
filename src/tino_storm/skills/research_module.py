from __future__ import annotations

import dspy
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - used for type hints only
    from .research import OutlineModule, DraftModule


class ResearchSignature(dspy.Signature):
    """Run outline and drafting in a single module."""

    topic = dspy.InputField("topic to research")
    outline = dspy.OutputField("brief outline")
    draft = dspy.OutputField("draft article")


@dataclass
class ResearchResult:
    outline: str
    draft: str


class ResearchModule(dspy.Module):
    """DSPy module that chains OutlineModule and DraftModule."""

    def __init__(self, outline: "OutlineModule", draft: "DraftModule") -> None:
        super().__init__()
        self.outline_module = outline
        self.draft_module = draft

    def forward(self, topic: str) -> ResearchResult:  # type: ignore[override]
        outline_pred = self.outline_module(topic=topic)
        draft_pred = self.draft_module(topic=topic, outline=outline_pred.outline)
        return ResearchResult(outline=outline_pred.outline, draft=draft_pred.draft)
