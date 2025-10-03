"""Top-level package for ``tino_storm`` with optional dependency helpers."""

import asyncio
from importlib import import_module
import sys
from types import ModuleType
from typing import TYPE_CHECKING

from ._extras import ensure_optional_dependency_stub

if TYPE_CHECKING:  # pragma: no cover
    from .search import search, search_sync

# Register helpful stubs for optional dependencies so that modules importing
# DSPy-related helpers raise ``MissingExtraError`` with installation guidance
# instead of failing with a bare ``ModuleNotFoundError`` when the ``llm`` extra
# is not installed.
ensure_optional_dependency_stub("dspy", "llm")
ensure_optional_dependency_stub("dspy.teleprompt", "llm")

__all__ = [
    "__version__",
    "STORMWikiRunnerArguments",
    "STORMWikiRunner",
    "STORMWikiLMConfigs",
    "CollaborativeStormLMConfigs",
    "RunnerArgument",
    "CoStormRunner",
    "ResearchSkill",
    "search",
    "search_async",
    "search_sync",
]

__version__ = "1.2.0"

_ATTR_MAP = {
    "STORMWikiRunnerArguments": (
        "tino_storm.storm_wiki.engine",
        "STORMWikiRunnerArguments",
    ),
    "STORMWikiRunner": ("tino_storm.storm_wiki.engine", "STORMWikiRunner"),
    "STORMWikiLMConfigs": ("tino_storm.storm_wiki.engine", "STORMWikiLMConfigs"),
    "CollaborativeStormLMConfigs": (
        "tino_storm.collaborative_storm.engine",
        "CollaborativeStormLMConfigs",
    ),
    "RunnerArgument": ("tino_storm.collaborative_storm.engine", "RunnerArgument"),
    "CoStormRunner": ("tino_storm.collaborative_storm.engine", "CoStormRunner"),
    "ResearchSkill": ("tino_storm.skills", "ResearchSkill"),
    "search": ("tino_storm.search", "search"),
    "search_async": ("tino_storm.search", "search_async"),
    "search_sync": ("tino_storm.search", "search_sync"),
}


def __getattr__(name: str):
    if name in _ATTR_MAP:
        module_name, attr = _ATTR_MAP[name]
        module = import_module(module_name)
        value = getattr(module, attr)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _dispatch_call(query: str, **kwargs):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        from .search import search_sync as _search_sync

        return _search_sync(query, **kwargs)
    else:
        from .search import search as _search

        return _search(query, **kwargs)


def __call__(query: str, **kwargs):
    return _dispatch_call(query, **kwargs)


class _CallableModule(ModuleType):
    def __call__(self, query: str, **kwargs):
        return _dispatch_call(query, **kwargs)


sys.modules[__name__].__class__ = _CallableModule
