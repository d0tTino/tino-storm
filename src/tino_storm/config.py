from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - used only for type checking
    from knowledge_storm.storm_wiki.engine import (
        STORMWikiRunnerArguments,
        STORMWikiLMConfigs,
    )


@dataclass
class StormConfig:
    """Aggregate configuration for running a STORM pipeline."""

    args: STORMWikiRunnerArguments
    lm_configs: STORMWikiLMConfigs
    rm: Any
