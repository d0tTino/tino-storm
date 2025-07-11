import sys
import types
import importlib.machinery
from dataclasses import dataclass
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))
sys.path.insert(0, str(ROOT_DIR))


# Stub modules from knowledge_storm to avoid heavy dependencies in tests


def pytest_configure(config):
    if "knowledge_storm" in sys.modules:
        return

    sys.path.insert(0, str(ROOT_DIR / "src"))
    sys.path.insert(0, str(ROOT_DIR))

    # --- dspy stubs ---
    dspy_mod = types.ModuleType("dspy")

    class _LM:
        def __init__(self, model: str = "stub"):
            self.model = model

        def basic_request(self, prompt, **kwargs):
            raise NotImplementedError

    dspy_mod.LM = _LM
    dspy_mod.Module = object

    dsp_submod = types.ModuleType("dspy.dsp")
    dsp_submod.LM = _LM
    dsp_submod.HFModel = _LM
    dspy_mod.dsp = dsp_submod

    sys.modules["dspy"] = dspy_mod
    sys.modules["dspy.dsp"] = dsp_submod

    # --- minimal requests stub ---
    if "requests" not in sys.modules:
        requests_mod = types.ModuleType("requests")
        sys.modules["requests"] = requests_mod

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

    # --- collaborative_storm.engine stub ---
    collab_engine_mod = types.ModuleType("knowledge_storm.collaborative_storm.engine")

    class CollaborativeStormLMConfigs:
        def __init__(self):
            self.question_answering_lm = None
            self.discourse_manage_lm = None
            self.utterance_polishing_lm = None
            self.warmstart_outline_gen_lm = None
            self.question_asking_lm = None
            self.knowledge_base_lm = None

        def set_question_answering_lm(self, lm):
            self.question_answering_lm = lm

        def set_discourse_manage_lm(self, lm):
            self.discourse_manage_lm = lm

        def set_utterance_polishing_lm(self, lm):
            self.utterance_polishing_lm = lm

        def set_warmstart_outline_gen_lm(self, lm):
            self.warmstart_outline_gen_lm = lm

        def set_question_asking_lm(self, lm):
            self.question_asking_lm = lm

        def set_knowledge_base_lm(self, lm):
            self.knowledge_base_lm = lm

        def to_dict(self):
            return {
                "question_answering_lm": {"model": self.question_answering_lm.model},
                "discourse_manage_lm": {"model": self.discourse_manage_lm.model},
                "utterance_polishing_lm": {"model": self.utterance_polishing_lm.model},
                "warmstart_outline_gen_lm": {
                    "model": self.warmstart_outline_gen_lm.model
                },
                "question_asking_lm": {"model": self.question_asking_lm.model},
                "knowledge_base_lm": {"model": self.knowledge_base_lm.model},
            }

        @classmethod
        def from_dict(cls, data):
            cfg = cls()
            for attr, kwargs in data.items():
                setattr(cfg, attr, LitellmModel(**kwargs))
            return cfg

    @dataclass
    class RunnerArgument:
        topic: str

        def to_dict(self):
            return {"topic": self.topic}

        @classmethod
        def from_dict(cls, data):
            return cls(**data)

    class CoStormRunner:
        def __init__(
            self,
            lm_config,
            runner_argument,
            logging_wrapper=None,
            rm=None,
            callback_handler=None,
        ):
            self.lm_config = lm_config
            self.runner_argument = runner_argument
            self.logging_wrapper = logging_wrapper
            self.rm = rm
            self.callback_handler = callback_handler
            self.knowledge_base = types.SimpleNamespace(
                to_dict=lambda: {"topic": runner_argument.topic}
            )
            self.discourse_manager = types.SimpleNamespace(
                serialize_experts=lambda: [], deserialize_experts=lambda x: None
            )

        def to_dict(self):
            return {
                "runner_argument": self.runner_argument.to_dict(),
                "lm_config": self.lm_config.to_dict(),
                "conversation_history": [],
                "warmstart_conv_archive": [],
                "experts": [],
                "knowledge_base": self.knowledge_base.to_dict(),
            }

        @classmethod
        def from_dict(cls, data, callback_handler=None):
            lm_config = CollaborativeStormLMConfigs.from_dict(data["lm_config"])
            runner_argument = RunnerArgument.from_dict(data["runner_argument"])
            runner = cls(
                lm_config=lm_config,
                runner_argument=runner_argument,
                logging_wrapper=None,
                callback_handler=callback_handler,
            )
            return runner

    collab_mod = types.ModuleType("knowledge_storm.collaborative_storm")
    collab_mod.engine = collab_engine_mod

    collab_engine_mod.CollaborativeStormLMConfigs = CollaborativeStormLMConfigs
    collab_engine_mod.RunnerArgument = RunnerArgument
    collab_engine_mod.CoStormRunner = CoStormRunner
    ks.CollaborativeStormLMConfigs = CollaborativeStormLMConfigs
    ks.RunnerArgument = RunnerArgument
    ks.CoStormRunner = CoStormRunner

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

    logging_wrapper_mod = types.ModuleType("knowledge_storm.logging_wrapper")

    class LoggingWrapper:
        def __init__(self, lm_config):
            self.lm_config = lm_config

        def log_pipeline_stage(self, pipeline_stage: str):
            class _Ctx:
                def __enter__(self_inner):
                    return None

                def __exit__(self_inner, exc_type, exc, tb):
                    return False

            return _Ctx()

        def log_event(self, event: str):
            return self.log_pipeline_stage(event)

        def dump_logging_and_reset(self):
            return {}

    logging_wrapper_mod.LoggingWrapper = LoggingWrapper

    ks.storm_wiki = storm_wiki_mod
    ks.collaborative_storm = collab_mod
    ks.lm = lm_mod
    ks.rm = rm_mod
    ks.utils = utils_mod
    ks.logging_wrapper = logging_wrapper_mod

    sys.modules["knowledge_storm"] = ks
    sys.modules["knowledge_storm.storm_wiki"] = storm_wiki_mod
    sys.modules["knowledge_storm.storm_wiki.engine"] = engine_mod
    sys.modules["knowledge_storm.collaborative_storm"] = collab_mod
    sys.modules["knowledge_storm.collaborative_storm.engine"] = collab_engine_mod
    sys.modules["knowledge_storm.lm"] = lm_mod
    sys.modules["knowledge_storm.rm"] = rm_mod
    sys.modules["knowledge_storm.utils"] = utils_mod
    sys.modules["knowledge_storm.logging_wrapper"] = logging_wrapper_mod
