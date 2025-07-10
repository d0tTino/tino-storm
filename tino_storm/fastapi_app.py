"""FastAPI endpoints exposing STORM functionalities."""

from __future__ import annotations

import os

from fastapi import FastAPI
from pydantic import BaseModel

from knowledge_storm import STORMWikiRunnerArguments, STORMWikiLMConfigs
from knowledge_storm.rm import DuckDuckGoSearchRM

from .config import StormConfig
from .storm import Storm


app = FastAPI(title="STORM API")


class OutlineRequest(BaseModel):
    topic: str
    ground_truth_url: str | None = None


def _create_storm() -> Storm:
    """Create a :class:`Storm` instance with default configuration."""
    args = STORMWikiRunnerArguments(
        output_dir=os.getenv("STORM_OUTPUT_DIR", "storm_output")
    )
    lm_configs = STORMWikiLMConfigs()
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        lm_configs.init_openai_model(
            openai_api_key=openai_key,
            azure_api_key=os.getenv("AZURE_API_KEY", ""),
            openai_type=os.getenv("OPENAI_API_TYPE", "openai"),
            api_base=os.getenv("AZURE_API_BASE"),
            api_version=os.getenv("AZURE_API_VERSION"),
        )
    rm = DuckDuckGoSearchRM(k=args.search_top_k)
    config = StormConfig(args=args, lm_configs=lm_configs, rm=rm)
    return Storm(config)


@app.post("/outline")
async def generate_outline(req: OutlineRequest):
    """Generate an outline for ``req.topic``."""
    storm = _create_storm()
    outline = storm.build_outline(
        req.topic, ground_truth_url=req.ground_truth_url or ""
    )
    return {"outline": outline.to_string()}


@app.post("/article")
async def generate_article(req: OutlineRequest):
    """Run the full pipeline to produce an article for ``req.topic``."""
    storm = _create_storm()
    article = storm.run_pipeline(req.topic, ground_truth_url=req.ground_truth_url or "")
    return {"article": article.to_string()}
