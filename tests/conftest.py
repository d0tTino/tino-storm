import sys
import types
import importlib.machinery
from dataclasses import dataclass
from pathlib import Path

# Stub modules from knowledge_storm to avoid heavy dependencies in tests


def pytest_configure(config):
    if "knowledge_storm" in sys.modules:
        return

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

    ks = types.ModuleType("knowledge_storm")
    ks.__spec__ = importlib.machinery.ModuleSpec(
        "knowledge_storm", loader=None, is_package=True
    )

    # --- storm_wiki.engine stubs ---
    engine_mod = types.ModuleType("knowledge_storm.storm_wiki.engine")

    @dataclass
    class STORMWikiRunnerArguments:
        output_dir: str
        max_conv_turn: int = 3
        max_perspective: int = 3
        max_search_queries_per_turn: int = 3
        disable_perspective: bool = False
        search_top_k: int = 3
        retrieve_top_k: int = 3
        max_thread_num: int = 10

    class STORMWikiLMConfigs:
        def __init__(self):
            self.conv_simulator_lm = None
            self.question_asker_lm = None
            self.outline_gen_lm = None
            self.article_gen_lm = None
            self.article_polish_lm = None

        def set_conv_simulator_lm(self, lm):
            self.conv_simulator_lm = lm

        def set_question_asker_lm(self, lm):
            self.question_asker_lm = lm

        def set_outline_gen_lm(self, lm):
            self.outline_gen_lm = lm

        def set_article_gen_lm(self, lm):
            self.article_gen_lm = lm

        def set_article_polish_lm(self, lm):
            self.article_polish_lm = lm

        def init_check(self):
            pass

    engine_mod.STORMWikiRunnerArguments = STORMWikiRunnerArguments
    engine_mod.STORMWikiLMConfigs = STORMWikiLMConfigs
    ks.STORMWikiRunnerArguments = STORMWikiRunnerArguments
    ks.STORMWikiLMConfigs = STORMWikiLMConfigs

    class STORMWikiRunner:
        def __init__(self, args, lm_configs, rm):
            self.args = args
            self.lm_configs = lm_configs
            self.rm = rm
            self.calls = []

        def build_outline(self, topic, ground_truth_url="", callback_handler=None):
            self.calls.append(("build_outline", topic, ground_truth_url))
            return f"outline:{topic}"

        def generate_article(self, callback_handler=None):
            self.calls.append(("generate_article",))
            return "article"

        def polish_article(self, remove_duplicate=False):
            self.calls.append(("polish_article", remove_duplicate))
            return "polished"

        def post_run(self):
            self.calls.append(("post_run",))

    class BaseCallbackHandler:
        pass

    ks.STORMWikiRunner = STORMWikiRunner
    ks.BaseCallbackHandler = BaseCallbackHandler

    storm_wiki_mod = types.ModuleType("knowledge_storm.storm_wiki")
    storm_wiki_mod.engine = engine_mod

    # --- lm stubs ---
    lm_mod = types.ModuleType("knowledge_storm.lm")

    class Base:
        def __init__(self, *args, **kwargs):
            pass

    class LitellmModel(Base):
        def __init__(self, model: str):
            self.model = model

    class OpenAIModel(Base):
        pass

    class AzureOpenAIModel(Base):
        pass

    class DeepSeekModel(Base):
        pass

    class GroqModel(Base):
        pass

    class ClaudeModel(Base):
        pass

    class VLLMClient(Base):
        pass

    class OllamaClient(Base):
        pass

    class TGIClient(Base):
        pass

    class TogetherClient(Base):
        pass

    class GoogleModel(Base):
        pass

    for cls in [
        LitellmModel,
        OpenAIModel,
        AzureOpenAIModel,
        DeepSeekModel,
        GroqModel,
        ClaudeModel,
        VLLMClient,
        OllamaClient,
        TGIClient,
        TogetherClient,
        GoogleModel,
    ]:
        setattr(lm_mod, cls.__name__, cls)

    # --- rm stubs ---
    rm_mod = types.ModuleType("knowledge_storm.rm")

    class YouRM:
        def __init__(self, *args, **kwargs):
            pass

    class BingSearch:
        def __init__(self, *args, **kwargs):
            pass

    class BraveRM:
        def __init__(self, *args, **kwargs):
            pass

    class SerperRM:
        def __init__(self, *args, **kwargs):
            pass

    class DuckDuckGoSearchRM:
        def __init__(self, *args, **kwargs):
            pass

    class TavilySearchRM:
        def __init__(self, *args, **kwargs):
            pass

    class VectorRM:
        def __init__(self, *args, **kwargs):
            pass

    class SearXNG:
        def __init__(self, *args, **kwargs):
            pass

    class AzureAISearch:
        def __init__(self, *args, **kwargs):
            pass

    class StanfordOvalArxivRM:
        def __init__(self, *args, **kwargs):
            pass

    for cls in [
        YouRM,
        BingSearch,
        BraveRM,
        SerperRM,
        DuckDuckGoSearchRM,
        TavilySearchRM,
        VectorRM,
        SearXNG,
        AzureAISearch,
        StanfordOvalArxivRM,
    ]:
        setattr(rm_mod, cls.__name__, cls)

    utils_mod = types.ModuleType("knowledge_storm.utils")

    def load_api_key(toml_file_path: str):
        return None

    utils_mod.load_api_key = load_api_key

    ks.storm_wiki = storm_wiki_mod
    ks.lm = lm_mod
    ks.rm = rm_mod
    ks.utils = utils_mod

    sys.modules["knowledge_storm"] = ks
    sys.modules["knowledge_storm.storm_wiki"] = storm_wiki_mod
    sys.modules["knowledge_storm.storm_wiki.engine"] = engine_mod
    sys.modules["knowledge_storm.lm"] = lm_mod
    sys.modules["knowledge_storm.rm"] = rm_mod
    sys.modules["knowledge_storm.utils"] = utils_mod
