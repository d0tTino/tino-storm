from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

from knowledge_storm import (
    STORMWikiRunnerArguments,
    STORMWikiRunner,
    STORMWikiLMConfigs,
)
from knowledge_storm.lm import LitellmModel
from knowledge_storm.rm import BingSearch


class ResearchRequest(BaseModel):
    topic: str
    output_dir: Optional[str] = "./results"


app = FastAPI(title="tino-storm API")


def _make_default_runner(output_dir: str) -> STORMWikiRunner:
    lm_configs = STORMWikiLMConfigs()
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


@app.post("/research")
def research(req: ResearchRequest):
    run_research(topic=req.topic, output_dir=req.output_dir)
    return {"status": "ok"}
