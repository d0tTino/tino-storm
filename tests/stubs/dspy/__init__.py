from types import SimpleNamespace

import importlib

__all__ = [
    "OpenAI",
    "LM",
    "HFModel",
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
    "dsp",
]


class OpenAI:
    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs


class LM:
    pass


class HFModel:
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

dsp = importlib.import_module("dsp")
