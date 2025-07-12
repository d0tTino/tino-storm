"""STORM Wiki pipeline powered entirely by GPT-4o.

This script is a minimal example of running STORM with GPT-4o for all
language model components. A search engine retriever provides external
information. Set the following environment variables before running:
    - OPENAI_API_KEY
    - OPENAI_API_TYPE ("openai" or "azure")
    - AZURE_API_BASE (if using Azure)
    - AZURE_API_VERSION (if using Azure)
    - One of YDC_API_KEY, BING_SEARCH_API_KEY, SERPER_API_KEY, BRAVE_API_KEY,
      TAVILY_API_KEY, or SEARXNG_API_KEY depending on the retriever.

Output will be structured as below
args.output_dir/
    topic_name/
        conversation_log.json
        raw_search_results.json
        direct_gen_outline.txt
        storm_gen_outline.txt
        url_to_info.json
        storm_gen_article.txt
        storm_gen_article_polished.txt
"""

import os
from argparse import ArgumentParser

from knowledge_storm import (
    STORMWikiRunnerArguments,
    STORMWikiRunner,
    STORMWikiLMConfigs,
)
from knowledge_storm.lm import OpenAIModel, AzureOpenAIModel
from tino_storm import get_retriever
from knowledge_storm.utils import load_api_key


def main(args):
    load_api_key(toml_file_path="secrets.toml")
    lm_configs = STORMWikiLMConfigs()
    openai_kwargs = {
        "api_key": os.getenv("OPENAI_API_KEY"),
        "temperature": 1.0,
        "top_p": 0.9,
    }

    ModelClass = (
        OpenAIModel if os.getenv("OPENAI_API_TYPE") == "openai" else AzureOpenAIModel
    )
    gpt4_name = "gpt-4o"
    if os.getenv("OPENAI_API_TYPE") == "azure":
        openai_kwargs["api_base"] = os.getenv("AZURE_API_BASE")
        openai_kwargs["api_version"] = os.getenv("AZURE_API_VERSION")

    conv_simulator_lm = ModelClass(model=gpt4_name, max_tokens=500, **openai_kwargs)
    question_asker_lm = ModelClass(model=gpt4_name, max_tokens=500, **openai_kwargs)
    outline_gen_lm = ModelClass(model=gpt4_name, max_tokens=400, **openai_kwargs)
    article_gen_lm = ModelClass(model=gpt4_name, max_tokens=700, **openai_kwargs)
    article_polish_lm = ModelClass(model=gpt4_name, max_tokens=4000, **openai_kwargs)

    lm_configs.set_conv_simulator_lm(conv_simulator_lm)
    lm_configs.set_question_asker_lm(question_asker_lm)
    lm_configs.set_outline_gen_lm(outline_gen_lm)
    lm_configs.set_article_gen_lm(article_gen_lm)
    lm_configs.set_article_polish_lm(article_polish_lm)

    engine_args = STORMWikiRunnerArguments(
        output_dir=args.output_dir,
        max_conv_turn=args.max_conv_turn,
        max_perspective=args.max_perspective,
        search_top_k=args.search_top_k,
        max_thread_num=args.max_thread_num,
    )

    rm_cls = get_retriever(args.retriever)
    rm_kwargs = {"k": engine_args.search_top_k}
    if args.retriever == "bing":
        rm_kwargs["bing_search_api_key"] = os.getenv("BING_SEARCH_API_KEY")
    elif args.retriever == "you":
        rm_kwargs["ydc_api_key"] = os.getenv("YDC_API_KEY")
    elif args.retriever == "brave":
        rm_kwargs["brave_search_api_key"] = os.getenv("BRAVE_API_KEY")
    elif args.retriever == "duckduckgo":
        rm_kwargs.update({"safe_search": "On", "region": "us-en"})
    elif args.retriever == "serper":
        rm_kwargs["serper_search_api_key"] = os.getenv("SERPER_API_KEY")
        rm_kwargs["query_params"] = {"autocorrect": True, "num": 10, "page": 1}
    elif args.retriever == "tavily":
        rm_kwargs["tavily_search_api_key"] = os.getenv("TAVILY_API_KEY")
        rm_kwargs["include_raw_content"] = True
    elif args.retriever == "searxng":
        rm_kwargs["searxng_api_key"] = os.getenv("SEARXNG_API_KEY")
    elif args.retriever == "azure_ai_search":
        rm_kwargs["azure_ai_search_api_key"] = os.getenv("AZURE_AI_SEARCH_API_KEY")
    rm = rm_cls(**rm_kwargs)

    runner = STORMWikiRunner(engine_args, lm_configs, rm)

    topic = input("Topic: ")
    runner.run(
        topic=topic,
        do_research=args.do_research,
        do_generate_outline=args.do_generate_outline,
        do_generate_article=args.do_generate_article,
        do_polish_article=args.do_polish_article,
    )
    runner.post_run()
    runner.summary()


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./results/gpt4_only",
        help="Directory to store the outputs.",
    )
    parser.add_argument(
        "--max-thread-num",
        type=int,
        default=3,
        help="Maximum number of threads to use. The information seeking part and the article generation "
        "part can speed up by using multiple threads. Consider reducing it if keep getting "
        '"Exceed rate limit" error when calling LM API.',
    )
    parser.add_argument(
        "--retriever",
        type=str,
        choices=[
            "bing",
            "you",
            "brave",
            "serper",
            "duckduckgo",
            "tavily",
            "searxng",
            "azure_ai_search",
        ],
        help="The search engine API to use for retrieving information.",
    )
    parser.add_argument(
        "--do-research",
        action="store_true",
        help="Simulate conversation to research the topic.",
    )
    parser.add_argument(
        "--do-generate-outline",
        action="store_true",
        help="Generate an outline for the topic instead of loading the results.",
    )
    parser.add_argument(
        "--do-generate-article",
        action="store_true",
        help="Generate an article for the topic instead of loading the results.",
    )
    parser.add_argument(
        "--do-polish-article",
        action="store_true",
        help="Polish the article by adding a summarization section and optionally removing duplicate content.",
    )
    parser.add_argument(
        "--max-conv-turn",
        type=int,
        default=3,
        help="Maximum number of questions in conversational question asking.",
    )
    parser.add_argument(
        "--max-perspective",
        type=int,
        default=3,
        help="Maximum number of perspectives to consider in perspective-guided question asking.",
    )
    parser.add_argument(
        "--search-top-k",
        type=int,
        default=3,
        help="Top k search results to consider for each search query.",
    )
    parser.add_argument(
        "--retrieve-top-k",
        type=int,
        default=3,
        help="Top k collected references for each section title.",
    )
    parser.add_argument(
        "--remove-duplicate",
        action="store_true",
        help="Remove duplicate content from the article if True.",
    )
    main(parser.parse_args())
