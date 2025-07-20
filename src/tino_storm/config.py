from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - used only for type checking
    from knowledge_storm.storm_wiki.engine import (
        STORMWikiRunnerArguments,
        STORMWikiLMConfigs,
    )


def create_retriever(name: str, k: int) -> Any:
    """Instantiate a retriever ``name`` using environment variables.

    ``name`` can be a single provider like ``"bing"`` or a comma separated list
    prefixed with ``"rrf="`` to compose a :class:`~tino_storm.rrf.RRFRetriever`.
    """
    import os

    from .providers import get_retriever

    if name.startswith("rrf="):
        from .rrf import RRFRetriever

        names = [n.strip() for n in name.split("=", 1)[1].split(",") if n.strip()]
        retrievers = [create_retriever(n, k) for n in names]
        return RRFRetriever(retrievers=retrievers, top_n=k)

    rm_cls = get_retriever(name)
    rm_kwargs = {"k": k}
    if name == "bing":
        rm_kwargs["bing_search_api_key"] = os.getenv("BING_SEARCH_API_KEY")
    elif name == "you":
        rm_kwargs["ydc_api_key"] = os.getenv("YDC_API_KEY")
    elif name == "brave":
        rm_kwargs["brave_search_api_key"] = os.getenv("BRAVE_API_KEY")
    elif name == "duckduckgo":
        rm_kwargs.update({"safe_search": "On", "region": "us-en"})
    elif name == "serper":
        rm_kwargs["serper_search_api_key"] = os.getenv("SERPER_API_KEY")
        rm_kwargs["query_params"] = {"autocorrect": True, "num": 10, "page": 1}
    elif name == "tavily":
        rm_kwargs["tavily_search_api_key"] = os.getenv("TAVILY_API_KEY")
        rm_kwargs["include_raw_content"] = True
    elif name == "searxng":
        rm_kwargs["searxng_api_key"] = os.getenv("SEARXNG_API_KEY")
    elif name == "azure_ai_search":
        rm_kwargs["azure_ai_search_api_key"] = os.getenv("AZURE_AI_SEARCH_API_KEY")
    return rm_cls(**rm_kwargs)


@dataclass
class StormConfig:
    """Aggregate configuration for running a STORM pipeline."""

    args: STORMWikiRunnerArguments
    lm_configs: STORMWikiLMConfigs
    rm: Any
    cloud_allowed: bool = True
    event_dir: Path = Path("events")

    @classmethod
    def from_env(cls) -> "StormConfig":
        """Create a configuration using environment variables or ``secrets.toml``."""
        import os

        from knowledge_storm.utils import load_api_key
        from knowledge_storm.storm_wiki.engine import (
            STORMWikiLMConfigs,
            STORMWikiRunnerArguments,
        )

        from .providers import get_llm

        load_api_key(toml_file_path="secrets.toml")

        output_dir = os.getenv("STORM_OUTPUT_DIR", "./results/from_env")
        retriever_name = os.getenv("STORM_RETRIEVER", "bing")
        event_dir = Path(os.getenv("STORM_EVENT_DIR", "events"))

        args = STORMWikiRunnerArguments(output_dir=output_dir)

        cloud_allowed = os.getenv("STORM_CLOUD_ALLOWED", "true").lower() != "false"

        openai_type = os.getenv("OPENAI_API_TYPE", "openai")
        llm_cls = get_llm(openai_type, cloud_allowed=cloud_allowed)

        openai_kwargs = {
            "api_key": os.getenv("OPENAI_API_KEY"),
            "temperature": 1.0,
            "top_p": 0.9,
        }
        if openai_type == "azure":
            openai_kwargs["api_base"] = os.getenv("AZURE_API_BASE")
            openai_kwargs["api_version"] = os.getenv("AZURE_API_VERSION")

        gpt_35 = "gpt-3.5-turbo" if openai_type == "openai" else "gpt-35-turbo"
        gpt_4 = "gpt-4o"

        conv_simulator_lm = llm_cls(model=gpt_35, max_tokens=500, **openai_kwargs)
        question_asker_lm = llm_cls(model=gpt_35, max_tokens=500, **openai_kwargs)
        outline_gen_lm = llm_cls(model=gpt_4, max_tokens=400, **openai_kwargs)
        article_gen_lm = llm_cls(model=gpt_4, max_tokens=700, **openai_kwargs)
        article_polish_lm = llm_cls(model=gpt_4, max_tokens=4000, **openai_kwargs)

        lm_configs = STORMWikiLMConfigs()
        lm_configs.set_conv_simulator_lm(conv_simulator_lm)
        lm_configs.set_question_asker_lm(question_asker_lm)
        lm_configs.set_outline_gen_lm(outline_gen_lm)
        lm_configs.set_article_gen_lm(article_gen_lm)
        lm_configs.set_article_polish_lm(article_polish_lm)

        rm = create_retriever(retriever_name, args.search_top_k)

        return cls(
            args=args,
            lm_configs=lm_configs,
            rm=rm,
            cloud_allowed=cloud_allowed,
            event_dir=event_dir,
        )
