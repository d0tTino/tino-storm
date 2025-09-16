from typing import Optional, List
import asyncio
import logging
import os
from dataclasses import asdict

try:
    from fastapi import FastAPI
    from pydantic import BaseModel
except ImportError as e:  # pragma: no cover - optional dependency
    raise ImportError(
        "fastapi is required for the API; install with 'tino-storm[research]'"
    ) from e

try:
    from knowledge_storm import (
        STORMWikiRunnerArguments,
        STORMWikiRunner,
        STORMWikiLMConfigs,
    )
    from knowledge_storm.lm import LitellmModel
    from knowledge_storm.rm import BingSearch
except ImportError as e:  # pragma: no cover - optional dependency
    raise ImportError(
        "knowledge-storm is required for research features; install with 'tino-storm[research]'"
    ) from e

from . import search
from .events import ResearchAdded, event_emitter


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


app = FastAPI(title="tino-storm API")


def _make_default_runner(output_dir: str) -> STORMWikiRunner:
    """Create a ``STORMWikiRunner`` with default language models.

    When the ``cloud_allowed`` environment variable is unset or evaluates to
    ``False`` the runner is configured to use the lightweight local model used
    by ``ResearchSkill``. Otherwise OpenAI models are used.
    """

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


@app.post("/research")
async def research(req: ResearchRequest):
    await asyncio.to_thread(
        run_research, topic=req.topic, output_dir=req.output_dir, vault=req.vault
    )
    return {"status": "ok"}


@app.post("/outline")
async def outline(req: ResearchRequest):
    await asyncio.to_thread(
        run_research,
        topic=req.topic,
        output_dir=req.output_dir,
        vault=req.vault,
        do_generate_article=False,
        do_polish_article=False,
    )
    return {"status": "ok"}


@app.post("/draft")
async def draft(req: ResearchRequest):
    await asyncio.to_thread(
        run_research,
        topic=req.topic,
        output_dir=req.output_dir,
        vault=req.vault,
        do_polish_article=False,
    )
    return {"status": "ok"}


@app.post("/ingest")
async def ingest(req: IngestRequest):
    from .ingest.watcher import VaultIngestHandler

    root = os.environ.get("STORM_VAULT_ROOT", "research")
    handler = VaultIngestHandler(root, vault=req.vault)
    await asyncio.to_thread(
        handler._ingest_text, req.text, req.source or "api", req.vault
    )
    return {"status": "ok"}


@app.post("/search")
async def search_endpoint(req: SearchRequest):
    result = await search(
        req.query,
        req.vaults,
        k_per_vault=req.k_per_vault,
        rrf_k=req.rrf_k,
    )
    return {"results": [asdict(r) for r in result]}
