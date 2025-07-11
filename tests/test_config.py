# knowledge_storm modules are stubbed in tests/conftest.py

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tino_storm.config import StormConfig
from knowledge_storm.storm_wiki.engine import (
    STORMWikiRunnerArguments,
    STORMWikiLMConfigs,
)
from knowledge_storm.lm import LitellmModel


def test_storm_config_initialization():
    args = STORMWikiRunnerArguments(output_dir="out")
    lm_configs = STORMWikiLMConfigs()
    lm_configs.set_conv_simulator_lm(LitellmModel(model="ollama/tinyllama"))
    cfg = StormConfig(args=args, lm_configs=lm_configs, rm="arxiv")

    assert cfg.args.output_dir == "out"
    assert cfg.lm_configs.conv_simulator_lm.model == "ollama/tinyllama"
    assert cfg.rm == "arxiv"


def test_storm_config_from_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk")
    monkeypatch.setenv("BING_SEARCH_API_KEY", "bing")
    monkeypatch.setenv("STORM_RETRIEVER", "bing")

    cfg = StormConfig.from_env()

    assert cfg.args.output_dir == "storm_output"
    assert cfg.lm_configs.conv_simulator_lm is not None
    assert cfg.rm.__class__.__name__ == "BingSearch"
