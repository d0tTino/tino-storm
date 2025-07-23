import os
import sys
import types

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
SRC_DIR = os.path.join(ROOT_DIR, "src")
if os.path.isdir(SRC_DIR) and SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# Provide light-weight stubs for optional dependencies so importing the
# engine module does not require installing the entire dependency stack.
for _missing in [
    "langchain_text_splitters",
    "trafilatura",
    "transformers",
]:
    if _missing not in sys.modules:
        module = types.ModuleType(_missing)
        if _missing == "langchain_text_splitters":

            class _DummySplitter:
                pass

            module.RecursiveCharacterTextSplitter = _DummySplitter
        elif _missing == "trafilatura":

            def extract(*_args, **_kwargs):
                return ""

            module.extract = extract
        elif _missing == "transformers":

            class _DummyTokenizer:
                @classmethod
                def from_pretrained(cls, *a, **kw):
                    return cls()

            module.AutoTokenizer = _DummyTokenizer
        sys.modules[_missing] = module

# Stub out additional optional dependencies used during import
for _missing in ["litellm", "openai", "dspy"]:
    if _missing not in sys.modules:
        module = types.ModuleType(_missing)
        if _missing == "dspy":
            dsp_sub = types.ModuleType("dsp")

            class LM:
                pass

            class HFModel:
                pass

            class Retrieve:
                pass

            dsp_sub.LM = LM
            dsp_sub.HFModel = HFModel
            dsp_sub.Retrieve = Retrieve
            module.dsp = dsp_sub
            module.Retrieve = Retrieve
        sys.modules[_missing] = module

# Minimal stubs for internal modules so that ``engine`` can be imported
# without pulling heavy dependencies. The serialization logic exercised by
# this test only relies on trivial behavior from these classes.
if "tino_storm.encoder" not in sys.modules:
    enc = types.ModuleType("tino_storm.encoder")

    class Encoder:
        pass

    enc.Encoder = Encoder
    sys.modules["tino_storm.encoder"] = enc

if "tino_storm.dataclass" not in sys.modules:
    dc = types.ModuleType("tino_storm.dataclass")

    class ConversationTurn:
        def __init__(self, **data):
            self.__dict__.update(data)

        def to_dict(self):
            return dict(self.__dict__)

        @classmethod
        def from_dict(cls, data):
            return cls(**data)

    class KnowledgeBase:
        def __init__(self, *a, **k):
            pass

        def to_dict(self):
            return {}

        @classmethod
        def from_dict(cls, data, **kwargs):
            return cls()

    dc.ConversationTurn = ConversationTurn
    dc.KnowledgeBase = KnowledgeBase
    sys.modules["tino_storm.dataclass"] = dc

if "tino_storm.interface" not in sys.modules:
    interface = types.ModuleType("tino_storm.interface")

    class LMConfigs:
        pass

    class Agent:
        pass

    interface.LMConfigs = LMConfigs
    interface.Agent = Agent
    sys.modules["tino_storm.interface"] = interface

if "tino_storm.lm" not in sys.modules:
    lm_mod = types.ModuleType("tino_storm.lm")

    class LitellmModel:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    lm_mod.LitellmModel = LitellmModel
    sys.modules["tino_storm.lm"] = lm_mod

if "tino_storm.rm" not in sys.modules:
    rm_mod = types.ModuleType("tino_storm.rm")

    class BingSearch:
        def __init__(self, k=0):
            self.k = k

    rm_mod.BingSearch = BingSearch
    sys.modules["tino_storm.rm"] = rm_mod

from tino_storm.collaborative_storm.engine import (  # noqa: E402
    CollaborativeStormLMConfigs,
    RunnerArgument,
    CoStormRunner,
)
from tino_storm.logging_wrapper import LoggingWrapper  # noqa: E402


def test_lm_config_round_trip():
    lm_config = CollaborativeStormLMConfigs()
    # initialize with a dummy provider to avoid network calls
    lm_config.init(lm_type="openai")
    args = RunnerArgument(topic="demo")
    os.environ.setdefault("ENCODER_API_TYPE", "openai")
    runner = CoStormRunner(
        lm_config=lm_config,
        runner_argument=args,
        logging_wrapper=LoggingWrapper(lm_config),
    )

    data = runner.to_dict()
    restored = CoStormRunner.from_dict(data)
    assert restored.lm_config.to_dict() == runner.lm_config.to_dict()
