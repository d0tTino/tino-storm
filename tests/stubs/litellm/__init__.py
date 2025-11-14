from types import SimpleNamespace

__all__ = ["completion", "text_completion", "drop_params", "telemetry", "cache"]

drop_params = False
telemetry = False
cache = None


def completion(*args, **kwargs):
    return {"choices": [{"message": SimpleNamespace(content="")}] , "usage": {}}


def text_completion(*args, **kwargs):
    return {"choices": [{"text": ""}], "usage": {}}
