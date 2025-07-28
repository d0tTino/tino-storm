import sys
import types

try:  # pragma: no cover - optional dependency
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover - fallback stubs
    fastapi = sys.modules.get("fastapi")
    if fastapi is None:
        fastapi = types.ModuleType("fastapi")
        sys.modules["fastapi"] = fastapi

    class FastAPI:
        def __init__(self, *a, **k):
            self.routes = {}

        def post(self, path, *a, **k):
            def decorator(fn):
                self.routes[path] = fn
                return fn

            return decorator

        def get(self, path, *a, **k):
            def decorator(fn):
                self.routes[path] = fn
                return fn

            return decorator

    class _Resp:
        def __init__(self, data):
            self.status_code = 200
            self._data = data

        def json(self):
            return self._data

    class TestClient:
        def __init__(self, app):
            self.app = app

        def post(self, path, json=None):
            fn = self.app.routes[path]
            data = dict(json or {})
            if path in {"/research", "/outline", "/draft"}:
                data.setdefault("output_dir", "./results")
                data.setdefault("vault", None)
            elif path == "/ingest":
                data.setdefault("source", None)
            arg = types.SimpleNamespace(**data)
            return _Resp(fn(arg))

    fastapi.FastAPI = FastAPI
    fastapi.testclient = types.ModuleType("fastapi.testclient")
    fastapi.testclient.TestClient = TestClient
    sys.modules["fastapi.testclient"] = fastapi.testclient
    globals().update({"FastAPI": FastAPI, "TestClient": TestClient})

from fastapi.testclient import TestClient  # type: ignore  # noqa: E402
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
        def __init__(self, root, **_kwargs):
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


def test_make_default_runner_local_model(monkeypatch):
    monkeypatch.delenv("cloud_allowed", raising=False)

    created = []

    class HFModel:
        def __init__(self, name, *a, **k):
            created.append(name)

    monkeypatch.setattr("dspy.HFModel", HFModel)

    from tino_storm import api

    runner = api._make_default_runner("./out")

    assert created == ["google/flan-t5-small"]
    lm_cfg = runner.lm_configs
    assert isinstance(lm_cfg.conv_simulator_lm, HFModel)
    assert lm_cfg.conv_simulator_lm is lm_cfg.question_asker_lm
    assert lm_cfg.conv_simulator_lm is lm_cfg.outline_gen_lm
    assert lm_cfg.conv_simulator_lm is lm_cfg.article_gen_lm
    assert lm_cfg.conv_simulator_lm is lm_cfg.article_polish_lm
