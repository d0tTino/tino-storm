from dataclasses import dataclass
from typing import Any

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
