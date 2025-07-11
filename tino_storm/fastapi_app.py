"""FastAPI endpoints exposing STORM functionalities."""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from .config import StormConfig
from .storm import Storm


app = FastAPI(title="STORM API")


class OutlineRequest(BaseModel):
    topic: str
    ground_truth_url: str | None = None


def _create_storm() -> Storm:
    """Create a :class:`Storm` instance with default configuration."""
    config = StormConfig.from_env()
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
