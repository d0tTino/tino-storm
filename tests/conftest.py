import sys
import types
import importlib.machinery
from dataclasses import dataclass
from pathlib import Path

# Add src to sys.path so packages are importable without installation
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

# Stub modules from knowledge_storm to avoid heavy dependencies in tests


def pytest_configure(config):
    if "knowledge_storm" in sys.modules:
        return

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

        def set_conv_simulator_lm(self, lm):
            self.conv_simulator_lm = lm

        def init_check(self):
            pass

    engine_mod.STORMWikiRunnerArguments = STORMWikiRunnerArguments
    engine_mod.STORMWikiLMConfigs = STORMWikiLMConfigs

    storm_wiki_mod = types.ModuleType("knowledge_storm.storm_wiki")
    storm_wiki_mod.engine = engine_mod

    # --- lm stubs ---
    lm_mod = types.ModuleType("knowledge_storm.lm")

    class Base:
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
        pass

    class BingSearch:
        pass

    class BraveRM:
        pass

    class SerperRM:
        pass

    class DuckDuckGoSearchRM:
        pass

    class TavilySearchRM:
        pass

    class VectorRM:
        pass

    class SearXNG:
        pass

    class AzureAISearch:
        pass

    class StanfordOvalArxivRM:
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

    ks.storm_wiki = storm_wiki_mod
    ks.lm = lm_mod
    ks.rm = rm_mod

    sys.modules["knowledge_storm"] = ks
    sys.modules["knowledge_storm.storm_wiki"] = storm_wiki_mod
    sys.modules["knowledge_storm.storm_wiki.engine"] = engine_mod
    sys.modules["knowledge_storm.lm"] = lm_mod
    sys.modules["knowledge_storm.rm"] = rm_mod
