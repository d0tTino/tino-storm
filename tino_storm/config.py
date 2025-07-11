from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

import os

from .providers import get_llm, get_retriever

if TYPE_CHECKING:  # pragma: no cover - used only for type checking
    from knowledge_storm.storm_wiki.engine import (
        STORMWikiRunnerArguments,
        STORMWikiLMConfigs,
    )


@dataclass
class StormConfig:
    """Aggregate configuration for running a STORM pipeline."""

    args: STORMWikiRunnerArguments
    lm_configs: STORMWikiLMConfigs
    rm: Any

    @classmethod
    def from_env(
        cls,
        *,
        retriever: str | None = None,
        output_dir: str | None = None,
        max_conv_turn: int | None = None,
        max_perspective: int | None = None,
        search_top_k: int | None = None,
        retrieve_top_k: int | None = None,
        max_thread_num: int | None = None,
    ) -> "StormConfig":
        """Create a :class:`StormConfig` using environment variables.

        The following environment variables are recognized:

        - ``OPENAI_API_KEY``: API key for OpenAI-compatible models.
        - ``OPENAI_API_TYPE``: name of the language model provider (``openai``,
          ``azure``, ``groq``, etc.).
        - ``AZURE_API_BASE`` / ``AZURE_API_VERSION``: Azure OpenAI parameters
          used when ``OPENAI_API_TYPE`` is ``azure``.
        - ``STORM_RETRIEVER``: retriever provider name (e.g. ``bing``).
        - ``BING_SEARCH_API_KEY`` and other provider-specific keys for
          retrievers.
        - ``STORM_OUTPUT_DIR``: directory for generated files.
        - ``STORM_MAX_CONV_TURN`` / ``STORM_MAX_PERSPECTIVE`` /
          ``STORM_SEARCH_TOP_K`` / ``STORM_RETRIEVE_TOP_K`` /
          ``STORM_MAX_THREAD_NUM``: numeric configuration options.
        """
        from knowledge_storm import STORMWikiRunnerArguments, STORMWikiLMConfigs
        from knowledge_storm.utils import load_api_key

        load_api_key(toml_file_path="secrets.toml")

        # --- language model setup ---
        openai_type = os.getenv("OPENAI_API_TYPE", "openai")
        llm_cls = get_llm(openai_type)
        llm_kwargs = {
            "api_key": os.getenv("OPENAI_API_KEY"),
            "temperature": 1.0,
            "top_p": 0.9,
        }
        if openai_type == "azure":
            llm_kwargs["api_base"] = os.getenv("AZURE_API_BASE")
            llm_kwargs["api_version"] = os.getenv("AZURE_API_VERSION")

        gpt_35 = "gpt-3.5-turbo" if openai_type == "openai" else "gpt-35-turbo"
        gpt_4 = "gpt-4o"

        conv_simulator_lm = llm_cls(model=gpt_35, max_tokens=500, **llm_kwargs)
        question_asker_lm = llm_cls(model=gpt_35, max_tokens=500, **llm_kwargs)
        outline_gen_lm = llm_cls(model=gpt_4, max_tokens=400, **llm_kwargs)
        article_gen_lm = llm_cls(model=gpt_4, max_tokens=700, **llm_kwargs)
        article_polish_lm = llm_cls(model=gpt_4, max_tokens=4000, **llm_kwargs)

        lm_configs = STORMWikiLMConfigs()
        lm_configs.set_conv_simulator_lm(conv_simulator_lm)
        lm_configs.set_question_asker_lm(question_asker_lm)
        lm_configs.set_outline_gen_lm(outline_gen_lm)
        lm_configs.set_article_gen_lm(article_gen_lm)
        lm_configs.set_article_polish_lm(article_polish_lm)

        # --- engine arguments ---
        output_dir = os.getenv("STORM_OUTPUT_DIR", output_dir or "storm_output")
        args = STORMWikiRunnerArguments(
            output_dir=output_dir,
            max_conv_turn=int(os.getenv("STORM_MAX_CONV_TURN", max_conv_turn or 3)),
            max_perspective=int(
                os.getenv("STORM_MAX_PERSPECTIVE", max_perspective or 3)
            ),
            search_top_k=int(os.getenv("STORM_SEARCH_TOP_K", search_top_k or 3)),
            retrieve_top_k=int(os.getenv("STORM_RETRIEVE_TOP_K", retrieve_top_k or 3)),
            max_thread_num=int(os.getenv("STORM_MAX_THREAD_NUM", max_thread_num or 10)),
        )

        # --- retriever ---
        rm_name = os.getenv("STORM_RETRIEVER", retriever or "duckduckgo")
        rm_cls = get_retriever(rm_name)
        rm_kwargs = {"k": args.search_top_k}
        if rm_name == "bing":
            rm_kwargs["bing_search_api_key"] = os.getenv("BING_SEARCH_API_KEY")
        elif rm_name == "you":
            rm_kwargs["ydc_api_key"] = os.getenv("YDC_API_KEY")
        elif rm_name == "brave":
            rm_kwargs["brave_search_api_key"] = os.getenv("BRAVE_API_KEY")
        elif rm_name == "serper":
            rm_kwargs["serper_search_api_key"] = os.getenv("SERPER_API_KEY")
            rm_kwargs["query_params"] = {"autocorrect": True, "num": 10, "page": 1}
        elif rm_name == "tavily":
            rm_kwargs["tavily_search_api_key"] = os.getenv("TAVILY_API_KEY")
            rm_kwargs["include_raw_content"] = True
        elif rm_name == "searxng":
            rm_kwargs["searxng_api_key"] = os.getenv("SEARXNG_API_KEY")
        elif rm_name == "azure_ai_search":
            rm_kwargs["azure_ai_search_api_key"] = os.getenv("AZURE_AI_SEARCH_API_KEY")
        rm = rm_cls(**rm_kwargs)

        return cls(args=args, lm_configs=lm_configs, rm=rm)
