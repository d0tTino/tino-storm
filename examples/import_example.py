"""Minimal import-based usage of STORM."""

import os
from knowledge_storm import (
    STORMWikiRunnerArguments,
    STORMWikiRunner,
    STORMWikiLMConfigs,
)
from tino_storm import get_llm, get_retriever


def main() -> None:
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
        topic="Quantum computing",
        do_research=True,
        do_generate_outline=True,
        do_generate_article=True,
    )
    print(article)


if __name__ == "__main__":
    main()
