import sys
import types
import asyncio
import dataclasses
import logging

from tino_storm.search_result import ResearchResult
from tino_storm.events import ResearchAdded, event_emitter

try:  # pragma: no cover - optional dependency
    from httpx import AsyncClient
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

    class AsyncClient:
        def __init__(self, app, base_url="http://test"):
            self.app = app

        async def post(self, path, json=None):
            fn = self.app.routes[path]
            data = dict(json or {})
            if path in {"/research", "/outline", "/draft"}:
                data.setdefault("output_dir", "./results")
                data.setdefault("vault", None)
            elif path == "/ingest":
                data.setdefault("source", None)
            elif path == "/search":
                data.setdefault("k_per_vault", 5)
                data.setdefault("rrf_k", 60)
            arg = types.SimpleNamespace(**data)
            return _Resp(fn(arg))

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

    fastapi.FastAPI = FastAPI
    httpx_mod = types.ModuleType("httpx")
    httpx_mod.AsyncClient = AsyncClient
    sys.modules["httpx"] = httpx_mod
    globals().update({"FastAPI": FastAPI, "AsyncClient": AsyncClient})
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


async def _post(path, payload):
    async with AsyncClient(app=app, base_url="http://test") as client:
        return await client.post(path, json=payload)


def test_research_endpoint(monkeypatch):
    runner_inst = dummy_runner_factory("./results")
    monkeypatch.setattr("tino_storm.api._make_default_runner", lambda dir_: runner_inst)

    resp = asyncio.run(_post("/research", {"topic": "ai"}))
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
    resp = asyncio.run(_post("/outline", {"topic": "ai"}))
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    kwargs = runner_inst.run_calls[0]
    assert not kwargs["do_generate_article"]
    assert not kwargs["do_polish_article"]


def test_draft_endpoint(monkeypatch):
    runner_inst = dummy_runner_factory("./results")
    monkeypatch.setattr("tino_storm.api._make_default_runner", lambda dir_: runner_inst)
    resp = asyncio.run(_post("/draft", {"topic": "ai"}))
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
    resp = asyncio.run(
        _post(
            "/ingest",
            {"text": "hello", "vault": "topic", "source": "src"},
        )
    )
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    assert captured == {
        "root": "research",
        "text": "hello",
        "source": "src",
        "vault": "topic",
    }


def test_search_endpoint(monkeypatch):
    called = {}

    async def fake_search(query, vaults, *, k_per_vault=5, rrf_k=60):
        called["args"] = (query, list(vaults), k_per_vault, rrf_k)
        return [ResearchResult(url="u", snippets=["s"], meta={})]

    monkeypatch.setattr("tino_storm.api.search", fake_search)
    resp = asyncio.run(_post("/search", {"query": "q", "vaults": ["v1", "v2"]}))
    assert resp.status_code == 200
    data = resp.json()
    first = data["results"][0]
    if not isinstance(first, dict):
        first = dataclasses.asdict(first)
    assert first == {"url": "u", "snippets": ["s"], "meta": {}, "summary": None}
    assert called["args"] == ("q", ["v1", "v2"], 5, 60)


def test_ingestion_failure_emits_event(monkeypatch, tmp_path, caplog):
    events: list[ResearchAdded] = []

    def handler(event: ResearchAdded) -> None:
        events.append(event)

    event_emitter.subscribe(ResearchAdded, handler)

    class RunnerWithArticle(DummyRunner):
        def run(self, **kwargs):
            super().run(**kwargs)
            path = tmp_path / "storm_gen_article_polished.txt"
            path.write_text("data")

    runner_inst = RunnerWithArticle(str(tmp_path))
    monkeypatch.setattr("tino_storm.api._make_default_runner", lambda dir_: runner_inst)

    class FailingHandler:
        def __init__(self, root, **kwargs):
            pass

        def _ingest_text(self, text, src, vault):
            raise RuntimeError("boom")

    monkeypatch.setattr("tino_storm.ingest.watcher.VaultIngestHandler", FailingHandler)

    with caplog.at_level(logging.ERROR):
        resp = asyncio.run(
            _post(
                "/research",
                {"topic": "t", "vault": "v", "output_dir": str(tmp_path)},
            )
        )

    event_emitter.unsubscribe(ResearchAdded, handler)

    assert resp.status_code == 200
    assert events and "error" in events[0].information_table
    assert "boom" in events[0].information_table["error"]
    assert "Error ingesting article" in caplog.text


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


def test_search_endpoint_asyncio(monkeypatch):
    """/search endpoint callable from asyncio."""

    called = {}

    async def fake_search(query, vaults, *, k_per_vault=5, rrf_k=60):
        called["args"] = (query, list(vaults), k_per_vault, rrf_k)
        return [ResearchResult(url="u", snippets=["s"], meta={})]

    monkeypatch.setattr("tino_storm.api.search", fake_search)

    async def _run():
        async with AsyncClient(app=app, base_url="http://test") as client:
            return await client.post(
                "/search", json={"query": "q", "vaults": ["v1", "v2"]}
            )

    resp = asyncio.run(_run())

    assert resp.status_code == 200
    data = resp.json()
    first = data["results"][0]
    if not isinstance(first, dict):
        first = dataclasses.asdict(first)
    assert first == {"url": "u", "snippets": ["s"], "meta": {}, "summary": None}
    assert called["args"] == ("q", ["v1", "v2"], 5, 60)
