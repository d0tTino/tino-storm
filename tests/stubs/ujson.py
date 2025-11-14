import json

__all__ = ["dumps", "loads"]


def dumps(obj, *args, **kwargs):
    return json.dumps(obj)


def loads(s, *args, **kwargs):
    return json.loads(s)
