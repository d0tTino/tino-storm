import argparse
from tino_storm.cli import make_config


def test_make_config(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk")
    monkeypatch.setenv("BING_SEARCH_API_KEY", "bing")
    args = argparse.Namespace(
        output_dir="out",
        max_conv_turn=2,
        max_perspective=4,
        search_top_k=5,
        retrieve_top_k=5,
        max_thread_num=1,
        retriever="bing",
    )
    cfg = make_config(args)

    assert cfg.args.output_dir == "out"
    assert cfg.args.max_conv_turn == 2
    assert cfg.lm_configs.conv_simulator_lm is not None
    assert cfg.rm.__class__.__name__ == "BingSearch"


def test_make_config_env_defaults(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk")
    monkeypatch.setenv("BING_SEARCH_API_KEY", "bing")
    monkeypatch.setenv("STORM_RETRIEVER", "bing")

    args = argparse.Namespace(
        output_dir=None,
        max_conv_turn=None,
        max_perspective=None,
        search_top_k=None,
        retrieve_top_k=None,
        max_thread_num=None,
        retriever=None,
    )

    cfg = make_config(args)

    assert cfg.args.output_dir == "storm_output"
    assert cfg.lm_configs.conv_simulator_lm is not None
    assert cfg.rm.__class__.__name__ == "BingSearch"
