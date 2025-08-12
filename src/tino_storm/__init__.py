"""Top-level package for ``tino_storm``.

Primary classes are exposed here via lazy imports to avoid heavy
dependencies unless needed."""

from importlib import import_module
import sys
from types import ModuleType
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .search import search

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
}


def __getattr__(name: str):
    if name in _ATTR_MAP:
        module_name, attr = _ATTR_MAP[name]
        module = import_module(module_name)
        value = getattr(module, attr)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __call__(query: str, **kwargs):
    return search(query, **kwargs)


class _CallableModule(ModuleType):
    def __call__(self, query: str, **kwargs):
        return search(query, **kwargs)


sys.modules[__name__].__class__ = _CallableModule
