import sys
import types

if "fastapi" in sys.modules:
    sys.modules.pop("fastapi")
    sys.modules.pop("fastapi.testclient", None)
if "pydantic" in sys.modules:
    sys.modules.pop("pydantic")
if "httpx" in sys.modules:
    sys.modules.pop("httpx")
from fastapi.testclient import TestClient

import knowledge_storm.storm_wiki.engine as ks_engine
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

from tino_storm.api import app  # noqa: E402


class DummyRunner:
    def __init__(self, dir_):
        self.args = types.SimpleNamespace(output_dir=dir_)
        self.run_calls = []
        self.post_called = 0

    def run(self, **kwargs):
        self.run_calls.append(kwargs)

    def post_run(self):
        self.post_called += 1


def dummy_runner_factory(output_dir):
    return DummyRunner(output_dir)


def test_research_endpoint(monkeypatch):
    runner_inst = dummy_runner_factory("./results")
    monkeypatch.setattr("tino_storm.api._make_default_runner", lambda dir_: runner_inst)

    client = TestClient(app)
    resp = client.post("/research", json={"topic": "ai"})
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    assert runner_inst.run_calls
    kwargs = runner_inst.run_calls[0]
    assert kwargs["do_research"]
    assert kwargs["do_generate_outline"]
    assert kwargs["do_generate_article"]
    assert kwargs["do_polish_article"]


def test_outline_endpoint(monkeypatch):
    runner_inst = dummy_runner_factory("./results")
    monkeypatch.setattr("tino_storm.api._make_default_runner", lambda dir_: runner_inst)
    client = TestClient(app)
    resp = client.post("/outline", json={"topic": "ai"})
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    kwargs = runner_inst.run_calls[0]
    assert not kwargs["do_generate_article"]
    assert not kwargs["do_polish_article"]


def test_draft_endpoint(monkeypatch):
    runner_inst = dummy_runner_factory("./results")
    monkeypatch.setattr("tino_storm.api._make_default_runner", lambda dir_: runner_inst)
    client = TestClient(app)
    resp = client.post("/draft", json={"topic": "ai"})
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    kwargs = runner_inst.run_calls[0]
    assert kwargs["do_generate_article"]
    assert not kwargs["do_polish_article"]


def test_ingest_endpoint(monkeypatch):
    captured = {}

    class DummyHandler:
        def __init__(self, root):
            captured["root"] = root

        def _ingest_text(self, text, src, vault):
            captured["text"] = text
            captured["source"] = src
            captured["vault"] = vault

    monkeypatch.setattr("tino_storm.ingest.watcher.VaultIngestHandler", DummyHandler)
    client = TestClient(app)
    resp = client.post(
        "/ingest",
        json={"text": "hello", "vault": "topic", "source": "src"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    assert captured == {
        "root": "research",
        "text": "hello",
        "source": "src",
        "vault": "topic",
    }
