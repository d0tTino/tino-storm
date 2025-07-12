"""High-level interface for running the STORM pipeline."""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - only for type checking
    from knowledge_storm import BaseCallbackHandler

from .config import StormConfig


class Storm:
    """Convenient wrapper around :class:`STORMWikiRunner`."""

    def __init__(self, config: StormConfig):
        from knowledge_storm import STORMWikiRunner

        self.config = config
        self.runner = STORMWikiRunner(config.args, config.lm_configs, config.rm)

    def build_outline(
        self,
        topic: str,
        ground_truth_url: str = "",
        callback_handler: Optional["BaseCallbackHandler"] = None,
    ):
        from knowledge_storm import BaseCallbackHandler

        return self.runner.build_outline(
            topic=topic,
            ground_truth_url=ground_truth_url,
            callback_handler=callback_handler or BaseCallbackHandler(),
        )

    def generate_article(
        self,
        callback_handler: Optional["BaseCallbackHandler"] = None,
    ):
        from knowledge_storm import BaseCallbackHandler

        return self.runner.generate_article(
            callback_handler=callback_handler or BaseCallbackHandler()
        )

    def polish_article(self, remove_duplicate: bool = False):
        return self.runner.polish_article(remove_duplicate=remove_duplicate)

    def run_pipeline(
        self,
        topic: str,
        ground_truth_url: str = "",
        remove_duplicate: bool = False,
        callback_handler: Optional["BaseCallbackHandler"] = None,
    ):
        self.build_outline(topic, ground_truth_url, callback_handler=callback_handler)
        self.generate_article(callback_handler=callback_handler)
        article = self.polish_article(remove_duplicate=remove_duplicate)
        self.runner.post_run()
        return article


def run_pipeline(
    config: StormConfig,
    topic: str,
    ground_truth_url: str = "",
    remove_duplicate: bool = False,
):
    """Run the full STORM pipeline with one function call."""
    storm = Storm(config)
    return storm.run_pipeline(topic, ground_truth_url, remove_duplicate)
