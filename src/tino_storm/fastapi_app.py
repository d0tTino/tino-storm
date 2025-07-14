"""FastAPI endpoints exposing STORM functionalities."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi import Query
from pydantic import BaseModel

from .config import StormConfig
from .providers import get_retriever
from .storm import Storm


app = FastAPI(title="STORM API")


class OutlineRequest(BaseModel):
    topic: str
    ground_truth_url: str | None = None


def _create_storm(
    *, output_dir: str | None = None, retriever: str | None = None
) -> Storm:
    """Create a :class:`Storm` instance using :func:`StormConfig.from_env`."""
    config = StormConfig.from_env()
    if output_dir is not None:
        config.args.output_dir = output_dir
    if retriever is None:
        import os

        retriever = os.getenv("STORM_RETRIEVER")
    if retriever is not None:
        rm_cls = get_retriever(retriever)
        config.rm = rm_cls(k=config.args.search_top_k)
    return Storm(config)


@app.post("/outline")
async def generate_outline(
    req: OutlineRequest,
    output_dir: str | None = Query(None),
    retriever: str | None = Query(None),
):
    """Generate an outline for ``req.topic``."""
    storm = _create_storm(output_dir=output_dir, retriever=retriever)
    outline = storm.build_outline(
        req.topic, ground_truth_url=req.ground_truth_url or ""
    )
    return {"outline": outline.to_string()}


@app.post("/article")
async def generate_article(
    req: OutlineRequest,
    output_dir: str | None = Query(None),
    retriever: str | None = Query(None),
):
    """Run the full pipeline to produce an article for ``req.topic``."""
    storm = _create_storm(output_dir=output_dir, retriever=retriever)
    article = storm.run_pipeline(req.topic, ground_truth_url=req.ground_truth_url or "")
    return {"article": article.to_string()}
