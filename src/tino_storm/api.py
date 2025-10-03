from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from . import search
from .events import ResearchAdded, event_emitter

if TYPE_CHECKING:  # pragma: no cover - imported for type hints only
    from knowledge_storm import STORMWikiRunner


@dataclass(frozen=True)
class _RequestModels:
    research: type
    ingest: type
    search: type


def _model_to_dict(instance: Any) -> Dict[str, Any]:
    """Return a plain dictionary for ``instance`` regardless of its origin."""

    if hasattr(instance, "model_dump"):
        return instance.model_dump()
    if hasattr(instance, "dict"):
        return instance.dict()
    if isinstance(instance, dict):
        return dict(instance)
    try:
        return dict(vars(instance))
    except TypeError as exc:  # pragma: no cover - defensive
        raise TypeError("Unsupported request payload type") from exc


def _emit_research_failure(topic: str, vault: Optional[str], exc: Exception) -> Dict[str, Any]:
    """Emit a ``ResearchAdded`` failure event and return the error payload."""

    info_table = {"error": str(exc)}
    event_emitter.emit_sync(
        ResearchAdded(topic=vault or topic, information_table=info_table)
    )
    return info_table


def _maybe_raise_http_error(detail: Dict[str, Any]) -> Optional[Exception]:
    """Return an ``HTTPException`` when FastAPI is available."""

    try:  # pragma: no cover - exercised when FastAPI is installed
        from fastapi import HTTPException  # type: ignore
    except Exception:  # pragma: no cover - optional dependency missing
        return None
    return HTTPException(status_code=500, detail={"status": "error", "detail": detail})


def _register_routes(app: Any, models: _RequestModels) -> None:
    """Attach API routes to ``app`` using the provided request models."""

    ResearchRequestModel = models.research
    IngestRequestModel = models.ingest
    SearchRequestModel = models.search

    async def _handle_research_request(
        data: Dict[str, Any],
        *,
        do_research: bool = True,
        do_generate_outline: bool = True,
        do_generate_article: bool = True,
        do_polish_article: bool = True,
    ) -> Dict[str, Any]:
        try:
            await asyncio.to_thread(
                run_research,
                topic=data["topic"],
                output_dir=data.get("output_dir", "./results"),
                vault=data.get("vault"),
                do_research=do_research,
                do_generate_outline=do_generate_outline,
                do_generate_article=do_generate_article,
                do_polish_article=do_polish_article,
            )
        except Exception as exc:  # noqa: BLE001
            logging.exception("Failed to start research for topic %s", data["topic"])
            detail = _emit_research_failure(data["topic"], data.get("vault"), exc)
            http_exc = _maybe_raise_http_error(detail)
            if http_exc is not None:
                raise http_exc
            return {"status": "error", "detail": detail}
        return {"status": "ok"}

    @app.post("/research")
    async def research(req: ResearchRequestModel) -> Dict[str, Any]:
        data = _model_to_dict(req)
        return await _handle_research_request(data)

    @app.post("/outline")
    async def outline(req: ResearchRequestModel) -> Dict[str, Any]:
        data = _model_to_dict(req)
        return await _handle_research_request(
            data,
            do_generate_article=False,
            do_polish_article=False,
        )

    @app.post("/draft")
    async def draft(req: ResearchRequestModel) -> Dict[str, Any]:
        data = _model_to_dict(req)
        return await _handle_research_request(
            data,
            do_polish_article=False,
        )

    @app.post("/ingest")
    async def ingest(req: IngestRequestModel) -> Dict[str, str]:
        data = _model_to_dict(req)
        from .ingest.watcher import VaultIngestHandler

        root = os.environ.get("STORM_VAULT_ROOT", "research")
        handler = VaultIngestHandler(root, vault=data["vault"])
        await asyncio.to_thread(
            handler._ingest_text,
            data["text"],
            data.get("source") or "api",
            data["vault"],
        )
        return {"status": "ok"}

    @app.post("/search")
    async def search_endpoint(req: SearchRequestModel) -> Dict[str, Any]:
        data = _model_to_dict(req)
        result = await search(
            data["query"],
            data["vaults"],
            k_per_vault=data.get("k_per_vault", 5),
            rrf_k=data.get("rrf_k", 60),
        )
        return {"results": [asdict(r) for r in result]}


def _create_fastapi_app():
    try:
        from fastapi import FastAPI
        from pydantic import BaseModel
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "fastapi is required for the API; install with 'tino-storm[research]'"
        ) from exc

    class ResearchRequest(BaseModel):
        topic: str
        output_dir: Optional[str] = "./results"
        vault: Optional[str] = None

    class IngestRequest(BaseModel):
        text: str
        vault: str
        source: Optional[str] = None

    class SearchRequest(BaseModel):
        query: str
        vaults: List[str]
        k_per_vault: int = 5
        rrf_k: int = 60

    fastapi_app = FastAPI(title="tino-storm API")
    _register_routes(
        fastapi_app,
        _RequestModels(
            research=ResearchRequest,
            ingest=IngestRequest,
            search=SearchRequest,
        ),
    )
    return fastapi_app


class _LazyFastAPIApp:
    """Proxy that creates the FastAPI app on first access."""

    __slots__ = ("_app",)

    def __init__(self) -> None:
        self._app = None

    def _ensure_app(self):
        if self._app is None:
            self._app = _create_fastapi_app()
        return self._app

    def __getattr__(self, name: str) -> Any:
        return getattr(self._ensure_app(), name)

    async def __call__(self, scope, receive, send):
        app = self._ensure_app()
        await app(scope, receive, send)


app = _LazyFastAPIApp()


def get_app():
    """Return the FastAPI application, instantiating it on demand."""

    return app._ensure_app()


def _make_default_runner(output_dir: str) -> "STORMWikiRunner":
    """Create a ``STORMWikiRunner`` with default language models.

    When the ``cloud_allowed`` environment variable is unset or evaluates to
    ``False`` the runner is configured to use the lightweight local model used
    by ``ResearchSkill``. Otherwise OpenAI models are used.
    """

    try:
        from knowledge_storm import (
            STORMWikiLMConfigs,
            STORMWikiRunner,
            STORMWikiRunnerArguments,
        )
        from knowledge_storm.lm import LitellmModel
        from knowledge_storm.rm import BingSearch
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "knowledge-storm is required for research features; install with 'tino-storm[research]'"
        ) from exc

    lm_configs = STORMWikiLMConfigs()

    cloud_allowed = os.environ.get("cloud_allowed", "").lower() in (
        "1",
        "true",
        "yes",
    )

    if not cloud_allowed:
        from dspy import HFModel

        local_model = HFModel("google/flan-t5-small")
        lm_configs.set_conv_simulator_lm(local_model)
        lm_configs.set_question_asker_lm(local_model)
        lm_configs.set_outline_gen_lm(local_model)
        lm_configs.set_article_gen_lm(local_model)
        lm_configs.set_article_polish_lm(local_model)
    else:
        openai_kwargs = {
            "api_key": None,
            "temperature": 1.0,
            "top_p": 0.9,
        }
        gpt_35 = LitellmModel(model="gpt-3.5-turbo", max_tokens=500, **openai_kwargs)
        gpt_4 = LitellmModel(model="gpt-4o", max_tokens=3000, **openai_kwargs)
        lm_configs.set_conv_simulator_lm(gpt_35)
        lm_configs.set_question_asker_lm(gpt_35)
        lm_configs.set_outline_gen_lm(gpt_4)
        lm_configs.set_article_gen_lm(gpt_4)
        lm_configs.set_article_polish_lm(gpt_4)

    args = STORMWikiRunnerArguments(output_dir=output_dir)
    rm = BingSearch(k=args.search_top_k)
    return STORMWikiRunner(args, lm_configs, rm)


def run_research(
    topic: str,
    output_dir: str = "./results",
    vault: Optional[str] = None,
    do_research: bool = True,
    do_generate_outline: bool = True,
    do_generate_article: bool = True,
    do_polish_article: bool = True,
) -> None:
    runner = _make_default_runner(output_dir)
    runner.run(
        topic=topic,
        do_research=do_research,
        do_generate_outline=do_generate_outline,
        do_generate_article=do_generate_article,
        do_polish_article=do_polish_article,
    )
    runner.post_run()

    if vault:
        try:
            from .ingest.watcher import VaultIngestHandler

            root = os.environ.get("STORM_VAULT_ROOT", "research")
            handler = VaultIngestHandler(root, vault=vault)

            article_path = os.path.join(
                runner.args.output_dir, "storm_gen_article_polished.txt"
            )
            if not os.path.exists(article_path):
                article_path = os.path.join(
                    runner.args.output_dir, "storm_gen_article.txt"
                )

            if os.path.exists(article_path):
                text = open(article_path, "r", encoding="utf-8").read()
                handler._ingest_text(text, article_path, vault)
        except Exception as exc:  # noqa: BLE001
            logging.exception("Error ingesting article for vault %s", vault)
            event_emitter.emit_sync(
                ResearchAdded(topic=vault, information_table={"error": str(exc)})
            )

