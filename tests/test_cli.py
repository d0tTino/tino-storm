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

    monkeypatch.setattr("tino_storm.cli.search", fake_search)

    main(["search", "--query", "ai", "--vaults", "science,notes"])

    out = capsys.readouterr().out
    assert calls == [("ai", ["science", "notes"], 5, 60)]
    assert "example.com" in out


def test_cli_ingest(monkeypatch, tmp_path):
    """ingest command initializes VaultIngestHandler with provided args."""

    captured = {}

    class DummyHandler:
        def __init__(self, root, **kwargs):
            captured["root"] = root
            captured.update(kwargs)

    monkeypatch.setattr("tino_storm.ingest.watcher.VaultIngestHandler", DummyHandler)

    def fake_start_watcher(**kwargs):
        from pathlib import Path

        watch_root = Path(kwargs.get("root") or "research").expanduser()
        DummyHandler(
            str(watch_root),
            chroma_path=kwargs.get("chroma_path"),
            twitter_limit=kwargs.get("twitter_limit"),
            reddit_limit=kwargs.get("reddit_limit"),
            fourchan_limit=kwargs.get("fourchan_limit"),
            reddit_client_id=kwargs.get("reddit_client_id"),
            reddit_client_secret=kwargs.get("reddit_client_secret"),
            vault=None,
        )

    monkeypatch.setattr("tino_storm.cli.start_watcher", fake_start_watcher)

    main(
        [
            "ingest",
            "--root",
            str(tmp_path),
            "--twitter-limit",
            "2",
            "--reddit-limit",
            "3",
            "--fourchan-limit",
            "4",
            "--reddit-client-id",
            "cid",
            "--reddit-client-secret",
            "sec",
        ]
    )

    assert captured == {
        "root": str(tmp_path),
        "chroma_path": None,
        "twitter_limit": 2,
        "reddit_limit": 3,
        "fourchan_limit": 4,
        "reddit_client_id": "cid",
        "reddit_client_secret": "sec",
        "vault": None,
    }
