from __future__ import annotations

import argparse
import os


from .config import StormConfig
from .providers import get_retriever
from .storm import Storm


def make_config(args: argparse.Namespace) -> StormConfig:
    """Create a :class:`StormConfig` from command line ``args``."""
    from knowledge_storm import (
        STORMWikiRunnerArguments,
        STORMWikiLMConfigs,
    )
    from knowledge_storm.lm import OpenAIModel, AzureOpenAIModel
    from knowledge_storm.utils import load_api_key

    load_api_key(toml_file_path="secrets.toml")

    openai_type = os.getenv("OPENAI_API_TYPE", "openai")
    openai_kwargs = {
        "api_key": os.getenv("OPENAI_API_KEY"),
        "temperature": 1.0,
        "top_p": 0.9,
    }
    if openai_type == "azure":
        openai_kwargs["api_base"] = os.getenv("AZURE_API_BASE")
        openai_kwargs["api_version"] = os.getenv("AZURE_API_VERSION")

    model_cls = OpenAIModel if openai_type == "openai" else AzureOpenAIModel
    gpt_35 = "gpt-3.5-turbo" if openai_type == "openai" else "gpt-35-turbo"
    gpt_4 = "gpt-4o"

    conv_simulator_lm = model_cls(model=gpt_35, max_tokens=500, **openai_kwargs)
    question_asker_lm = model_cls(model=gpt_35, max_tokens=500, **openai_kwargs)
    outline_gen_lm = model_cls(model=gpt_4, max_tokens=400, **openai_kwargs)
    article_gen_lm = model_cls(model=gpt_4, max_tokens=700, **openai_kwargs)
    article_polish_lm = model_cls(model=gpt_4, max_tokens=4000, **openai_kwargs)

    lm_configs = STORMWikiLMConfigs()
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
        retrieve_top_k=args.retrieve_top_k,
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

    return StormConfig(engine_args, lm_configs, rm)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the STORM pipeline")
    parser.add_argument(
        "--output-dir", type=str, default="./results/cli", help="Directory for outputs"
    )
    parser.add_argument(
        "--max-thread-num", type=int, default=3, help="Maximum number of threads"
    )
    parser.add_argument(
        "--retriever",
        type=str,
        required=True,
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
        help="Search engine to use",
    )
    parser.add_argument("--max-conv-turn", type=int, default=3)
    parser.add_argument("--max-perspective", type=int, default=3)
    parser.add_argument("--search-top-k", type=int, default=3)
    parser.add_argument("--retrieve-top-k", type=int, default=3)
    parser.add_argument(
        "--remove-duplicate", action="store_true", help="Remove duplicate text"
    )
    args = parser.parse_args(argv)

    config = make_config(args)
    storm = Storm(config)
    topic = input("Topic: ")
    article = storm.run_pipeline(topic, remove_duplicate=args.remove_duplicate)
    print(article)


if __name__ == "__main__":  # pragma: no cover - manual invocation
    main()
