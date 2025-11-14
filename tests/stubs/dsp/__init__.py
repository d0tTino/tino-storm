from types import SimpleNamespace, ModuleType

__all__ = [
    "LM",
    "HFModel",
    "OpenAI",
    "OllamaLocal",
    "OllamaClient",
    "HFClientTGI",
    "Together",
    "Retrieve",
    "Signature",
    "Module",
    "Predict",
    "Prediction",
    "ChainOfThought",
    "InputField",
    "OutputField",
    "settings",
    "ERRORS",
    "backoff_hdlr",
    "giveup_hdlr",
    "modules",
]


class LM:
    pass


class HFModel:
    pass


class OpenAI:
    def __init__(self, *args, **kwargs):
        pass


class OllamaLocal:
    def __init__(self, *args, **kwargs):
        pass


class OllamaClient:
    def __init__(self, *args, **kwargs):
        pass


class HFClientTGI:
    def __init__(self, *args, **kwargs):
        pass


class Together:
    pass


class Retrieve:
    def __init__(self, k: int = 3, **kwargs):
        self.k = k

    def __call__(self, *args, **kwargs):
        return []


class Signature:
    pass


class Module:
    def __init__(self, *args, **kwargs):
        pass


class Predict:
    def __init__(self, *args, **kwargs):
        self.result = SimpleNamespace()

    def __call__(self, *args, **kwargs):
        return self.result


class Prediction(SimpleNamespace):
    pass


class ChainOfThought(Predict):
    pass


class InputField:
    def __init__(self, *args, **kwargs):
        pass


class OutputField(InputField):
    pass


class settings:
    class context:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return None

        def __exit__(self, *args):
            return False


def backoff_hdlr(*args, **kwargs):
    pass


def giveup_hdlr(*args, **kwargs):
    return False


ERRORS = Exception

modules = ModuleType("dsp.modules")
modules.hf = ModuleType("dsp.modules.hf")
modules.hf_client = ModuleType("dsp.modules.hf_client")
modules.lm = ModuleType("dsp.modules.lm")
modules.lm.LM = LM
