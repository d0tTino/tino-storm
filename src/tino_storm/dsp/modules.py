from typing import Iterable, Dict, Optional

import dspy


class OutlineModule(dspy.Module):
    """Minimal outline generation module."""

    def __init__(self, lm: Optional[dspy.dsp.LM] = None):
        super().__init__()
        self.lm = lm or dspy.dsp.LM()

    def forward(self, topic: str, information_table=None, callback_handler=None):
        if hasattr(self.lm, "basic_request"):
            return self.lm.basic_request(f"outline:{topic}")
        return f"outline:{topic}"

    # Maintain compatibility with ResearchSkill
    def generate_outline(self, topic: str, information_table=None, callback_handler=None):
        return self.forward(topic, information_table, callback_handler)

    def evaluate(self, dataset: Iterable[Dict[str, str]]):
        """Return accuracy over ``dataset`` where each item has ``topic`` and ``expected``."""
        total = 0
        correct = 0
        for sample in dataset:
            total += 1
            pred = self.forward(sample["topic"])
            if pred == sample.get("expected"):
                correct += 1
        return correct / total if total else 0.0


class DraftModule(dspy.Module):
    """Minimal draft generation module."""

    def __init__(self, lm: Optional[dspy.dsp.LM] = None):
        super().__init__()
        self.lm = lm or dspy.dsp.LM()

    def forward(
        self,
        topic: str,
        information_table=None,
        article_with_outline: str | None = None,
        callback_handler=None,
    ):
        if hasattr(self.lm, "basic_request"):
            return self.lm.basic_request(f"draft:{topic}")
        return f"draft:{topic}"

    def generate_article(
        self,
        topic: str,
        information_table=None,
        article_with_outline: str | None = None,
        callback_handler=None,
    ):
        return self.forward(
            topic,
            information_table=information_table,
            article_with_outline=article_with_outline,
            callback_handler=callback_handler,
        )

    def evaluate(self, dataset: Iterable[Dict[str, str]]):
        total = 0
        correct = 0
        for sample in dataset:
            total += 1
            pred = self.forward(sample["topic"])
            if pred == sample.get("expected"):
                correct += 1
        return correct / total if total else 0.0


class PolishModule(dspy.Module):
    """Minimal polishing module."""

    def __init__(self, lm: Optional[dspy.dsp.LM] = None):
        super().__init__()
        self.lm = lm or dspy.dsp.LM()

    def forward(self, topic: str, draft_article: str, remove_duplicate: bool = False):
        if hasattr(self.lm, "basic_request"):
            return self.lm.basic_request(f"polish:{topic}")
        return f"polish:{topic}"

    def polish_article(self, topic: str, draft_article, remove_duplicate: bool = False):
        return self.forward(topic, draft_article, remove_duplicate)

    def evaluate(self, dataset: Iterable[Dict[str, str]]):
        total = 0
        correct = 0
        for sample in dataset:
            total += 1
            pred = self.forward(sample["topic"], draft_article="")
            if pred == sample.get("expected"):
                correct += 1
        return correct / total if total else 0.0
