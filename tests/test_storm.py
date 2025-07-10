from tino_storm.storm import Storm
from tino_storm.config import StormConfig
from knowledge_storm.storm_wiki.engine import (
    STORMWikiRunnerArguments,
    STORMWikiLMConfigs,
)
from knowledge_storm.rm import BingSearch


class DummyRM(BingSearch):
    pass


def make_config():
    args = STORMWikiRunnerArguments(output_dir="out")
    lm_cfgs = STORMWikiLMConfigs()
    return StormConfig(args=args, lm_configs=lm_cfgs, rm=DummyRM())


def test_build_outline_calls_runner(monkeypatch):
    cfg = make_config()
    storm = Storm(cfg)
    result = storm.build_outline("topic", "url")

    assert result == "outline:topic"
    assert storm.runner.calls == [("build_outline", "topic", "url")]


def test_run_pipeline_sequence(monkeypatch):
    cfg = make_config()
    storm = Storm(cfg)
    article = storm.run_pipeline("topic", "url", remove_duplicate=True)

    assert article == "polished"
    assert storm.runner.calls == [
        ("build_outline", "topic", "url"),
        ("generate_article",),
        ("polish_article", True),
        ("post_run",),
    ]
