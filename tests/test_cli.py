import argparse
import sys
import types
from tino_storm.cli import make_config, main
from tino_storm.storm import Storm


def _setup_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk")
    monkeypatch.setenv("BING_SEARCH_API_KEY", "bing")


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


def test_run_uses_topic_arg(monkeypatch):
    _setup_env(monkeypatch)
    recorded = {}

    def run_pipeline(
        self, topic: str, ground_truth_url: str = "", remove_duplicate: bool = False
    ):
        recorded["topic"] = topic
        return "article"

    monkeypatch.setattr(Storm, "run_pipeline", run_pipeline)
    main(["run", "--retriever", "bing", "--topic", "cats"])

    assert recorded["topic"] == "cats"


def test_run_prompts_for_topic(monkeypatch):
    _setup_env(monkeypatch)
    recorded = {}

    def run_pipeline(
        self, topic: str, ground_truth_url: str = "", remove_duplicate: bool = False
    ):
        recorded["topic"] = topic
        return "article"

    monkeypatch.setattr(Storm, "run_pipeline", run_pipeline)
    monkeypatch.setattr("builtins.input", lambda _: "dogs")
    main(["run", "--retriever", "bing"])

    assert recorded["topic"] == "dogs"


def test_ingest_calls_watch_vault(monkeypatch):
    recorded = {}

    stub = types.ModuleType("tino_storm.ingest")

    def watch(vault: str) -> None:
        recorded["vault"] = vault

    stub.watch_vault = watch
    monkeypatch.setitem(sys.modules, "tino_storm.ingest", stub)
    main(["ingest", "--vault", "v"])

    assert recorded["vault"] == "v"
