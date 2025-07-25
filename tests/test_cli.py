import os
import sys
import types

import knowledge_storm.storm_wiki.engine as ks_engine

# Expose required classes on the package root if not already provided
import knowledge_storm

for attr in [
    "STORMWikiRunnerArguments",
    "STORMWikiRunner",
    "STORMWikiLMConfigs",
]:
    if not hasattr(knowledge_storm, attr):
        setattr(knowledge_storm, attr, getattr(ks_engine, attr))

if "knowledge_storm.rm" not in sys.modules:
    rm_mod = types.ModuleType("knowledge_storm.rm")

    class BingSearch:
        def __init__(self, k=0):
            self.k = k

    rm_mod.BingSearch = BingSearch
    sys.modules["knowledge_storm.rm"] = rm_mod

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from tino_storm.cli import main  # noqa: E402


def test_cli_research_creates_files(tmp_path, monkeypatch):
    """Ensure CLI research command writes expected files using dummy runner."""

    def dummy_runner_factory(output_dir):
        class DummyRunner:
            def __init__(self, dir_):
                self.args = types.SimpleNamespace(output_dir=dir_)

            def run(self, **kwargs):
                os.makedirs(self.args.output_dir, exist_ok=True)
                with open(
                    os.path.join(self.args.output_dir, "storm_gen_article.txt"), "w"
                ) as f:
                    f.write("dummy")

            def post_run(self):
                with open(
                    os.path.join(self.args.output_dir, "run_config.json"), "w"
                ) as f:
                    f.write("{}")
                with open(
                    os.path.join(self.args.output_dir, "llm_call_history.jsonl"), "w"
                ) as f:
                    f.write("{}\n")

        return DummyRunner(output_dir)

    monkeypatch.setattr("tino_storm.api._make_default_runner", dummy_runner_factory)

    main(["research", "demo", "--output-dir", str(tmp_path)])

    assert (tmp_path / "storm_gen_article.txt").exists()
    assert (tmp_path / "run_config.json").exists()
    assert (tmp_path / "llm_call_history.jsonl").exists()


def test_cli_run_with_vault(tmp_path, monkeypatch):
    """Ensure new run sub-command accepts vault option."""

    def dummy_runner_factory(output_dir):
        class DummyRunner:
            def __init__(self, dir_):
                self.args = types.SimpleNamespace(output_dir=dir_)

            def run(self, **kwargs):
                os.makedirs(self.args.output_dir, exist_ok=True)
                with open(
                    os.path.join(self.args.output_dir, "storm_gen_article.txt"), "w"
                ) as f:
                    f.write("dummy")

            def post_run(self):
                with open(
                    os.path.join(self.args.output_dir, "run_config.json"), "w"
                ) as f:
                    f.write("{}")
                with open(
                    os.path.join(self.args.output_dir, "llm_call_history.jsonl"), "w"
                ) as f:
                    f.write("{}\n")

        return DummyRunner(output_dir)

    monkeypatch.setattr("tino_storm.api._make_default_runner", dummy_runner_factory)

    main(
        [
            "run",
            "--topic",
            "demo",
            "--vault",
            "test",
            "--output-dir",
            str(tmp_path),
        ]
    )

    assert (tmp_path / "storm_gen_article.txt").exists()
    assert (tmp_path / "run_config.json").exists()
    assert (tmp_path / "llm_call_history.jsonl").exists()


def test_cli_search(monkeypatch, capsys):
    """Search command queries vaults and prints results."""

    calls = []

    def fake_search(query, vaults, *, k_per_vault=5, rrf_k=60, chroma_path=None):
        calls.append((query, list(vaults), k_per_vault, rrf_k))
        return [{"url": "example.com", "snippets": ["result"]}]

    monkeypatch.setattr("tino_storm.ingest.search_vaults", fake_search)
    monkeypatch.setattr("tino_storm.cli.search_vaults", fake_search)

    main(["search", "--query", "ai", "--vaults", "science,notes"])

    out = capsys.readouterr().out
    assert calls == [("ai", ["science", "notes"], 5, 60)]
    assert "example.com" in out

