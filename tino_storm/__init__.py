from __future__ import annotations

from typing import Optional

from knowledge_storm import BaseCallbackHandler

from .config import StormConfig
from .storm import Storm, run_pipeline


def build_outline(
    config: StormConfig,
    topic: str,
    ground_truth_url: str = "",
    callback_handler: Optional[BaseCallbackHandler] = None,
):
    """Generate an outline for ``topic`` using ``config``."""
    return Storm(config).build_outline(
        topic=topic,
        ground_truth_url=ground_truth_url,
        callback_handler=callback_handler,
    )


def generate_article(
    config: StormConfig,
    callback_handler: Optional[BaseCallbackHandler] = None,
):
    """Generate an article using the previously built outline."""
    return Storm(config).generate_article(callback_handler=callback_handler)


def polish_article(config: StormConfig, remove_duplicate: bool = False):
    """Polish the generated article."""
    return Storm(config).polish_article(remove_duplicate=remove_duplicate)


__all__ = [
    "Storm",
    "run_pipeline",
    "build_outline",
    "generate_article",
    "polish_article",
    "StormConfig",
]
