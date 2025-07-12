"""Simple CLI wrapper around STORM."""

import argparse
import os

from knowledge_storm import (
    STORMWikiRunnerArguments,
    STORMWikiRunner,
    STORMWikiLMConfigs,
)
from tino_storm import get_llm, get_retriever


def run(topic: str) -> None:
    args = STORMWikiRunnerArguments()
    lm_configs = STORMWikiLMConfigs()
    Model = get_llm("openai")
    Retriever = get_retriever("bing")

    openai_lm = Model(model="gpt-3.5-turbo", api_key=os.getenv("OPENAI_API_KEY"))
    lm_configs.set_conv_simulator_lm(openai_lm)
    lm_configs.set_question_asker_lm(openai_lm)
    lm_configs.set_outline_gen_lm(openai_lm)
    lm_configs.set_article_gen_lm(openai_lm)

    rm = Retriever(
        bing_search_api_key=os.getenv("BING_SEARCH_API_KEY"), k=args.search_top_k
    )

    runner = STORMWikiRunner(args, lm_configs, rm)
    article = runner.run(
        topic=topic,
        do_research=True,
        do_generate_outline=True,
        do_generate_article=True,
    )
    print(article)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run STORM from the command line")
    parser.add_argument("topic", help="Topic to research")
    args = parser.parse_args()
    run(args.topic)


if __name__ == "__main__":
    main()
