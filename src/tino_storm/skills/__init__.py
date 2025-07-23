"""Light-weight research skill modules."""

from importlib import import_module

__all__ = ["ResearchSkill", "ResearchModule"]

_ATTR_MAP = {
    "ResearchSkill": ("tino_storm.skills.research", "ResearchSkill"),
    "ResearchModule": ("tino_storm.skills.research_module", "ResearchModule"),
}


def __getattr__(name: str):
    if name in _ATTR_MAP:
        module_name, attr = _ATTR_MAP[name]
        module = import_module(module_name)
        value = getattr(module, attr)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
