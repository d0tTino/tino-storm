# knowledge_storm modules are stubbed in tests/conftest.py

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

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
    cfg = StormConfig(args=args, lm_configs=lm_configs, rm="arxiv", vaults=["v1"])

    assert cfg.args.output_dir == "out"
    assert cfg.lm_configs.conv_simulator_lm.model == "ollama/tinyllama"
    assert cfg.rm == "arxiv"


def test_storm_config_from_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk")
    monkeypatch.setenv("BING_SEARCH_API_KEY", "bing")
    monkeypatch.setenv("STORM_RETRIEVER", "bing")
    cfg = StormConfig.from_env()

    assert cfg.lm_configs.conv_simulator_lm is not None
    assert cfg.rm.__class__.__name__ == "BingSearch"
    assert cfg.cloud_allowed is True


def test_storm_config_cloud_disabled(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk")
    monkeypatch.setenv("BING_SEARCH_API_KEY", "bing")
    monkeypatch.setenv("STORM_RETRIEVER", "bing")
    monkeypatch.setenv("STORM_CLOUD_ALLOWED", "false")
    monkeypatch.setenv("OPENAI_API_TYPE", "vllm")
    cfg = StormConfig.from_env()

    assert cfg.cloud_allowed is False


def test_storm_config_cloud_block(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk")
    monkeypatch.setenv("BING_SEARCH_API_KEY", "bing")
    monkeypatch.setenv("STORM_RETRIEVER", "bing")
    monkeypatch.setenv("STORM_CLOUD_ALLOWED", "false")
    with pytest.raises(ValueError):
        StormConfig.from_env()


def test_storm_config_custom_llm(monkeypatch):
    class CustomModel:
        def __init__(self, *args, **kwargs):
            pass

    from tino_storm import providers

    monkeypatch.setitem(providers.llm.LLM_REGISTRY, "custom", "CustomModel")
    monkeypatch.setattr(
        sys.modules["knowledge_storm.lm"], "CustomModel", CustomModel, raising=False
    )
    monkeypatch.setenv("OPENAI_API_KEY", "sk")
    monkeypatch.setenv("BING_SEARCH_API_KEY", "bing")
    monkeypatch.setenv("STORM_RETRIEVER", "bing")
    monkeypatch.setenv("OPENAI_API_TYPE", "custom")

    cfg = StormConfig.from_env()

    assert cfg.lm_configs.conv_simulator_lm.__class__.__name__ == "CustomModel"


def test_storm_config_invalid_llm(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk")
    monkeypatch.setenv("BING_SEARCH_API_KEY", "bing")
    monkeypatch.setenv("STORM_RETRIEVER", "bing")
    monkeypatch.setenv("OPENAI_API_TYPE", "missing")

    with pytest.raises(ValueError):
        StormConfig.from_env()
