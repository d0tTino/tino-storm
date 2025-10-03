"""Helpers for managing optional dependencies.

This module centralises the logic used across the codebase for importing
optional packages.  Heavy integrations such as LiteLLM and DSPy are moved to
extras so the baseline vault search experience only pulls lightweight
dependencies.  When one of those extras is missing we raise a descriptive error
that explains how to install the required extra instead of exposing a generic
``ModuleNotFoundError``.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
from types import ModuleType

__all__ = ["MissingExtraError", "require_extra", "ensure_optional_dependency_stub"]


class MissingExtraError(ImportError):
    """Raised when an optional dependency is accessed without its extra."""

    def __init__(self, package: str, extra: str) -> None:
        message = (
            f"The optional dependency '{package}' is required for this feature. "
            f"Install it with `pip install tino-storm[{extra}]`."
        )
        super().__init__(message)
        self.package = package
        self.extra = extra


def require_extra(module: str, extra: str, *, package: str | None = None) -> ModuleType:
    """Import *module* raising :class:`MissingExtraError` on failure.

    Parameters
    ----------
    module:
        The fully qualified module name to import.
    extra:
        The name of the optional extra that installs the dependency.
    package:
        Optional name of the PyPI package providing *module*.  When omitted the
        top-level module name is used.
    """

    target = package or module.split(".", 1)[0]

    try:
        return importlib.import_module(module)
    except ModuleNotFoundError as exc:
        if exc.name == target or exc.name == module:
            raise MissingExtraError(target, extra) from exc
        raise


def ensure_optional_dependency_stub(module: str, extra: str) -> None:
    """Register a lightweight stub that surfaces :class:`MissingExtraError`.

    The stub behaves like a namespace package so that ``import foo.bar`` works
    even when ``foo`` is missing.  Accessing any attribute of the stub raises a
    ``MissingExtraError`` explaining which extra to install.
    """

    if module in sys.modules:
        return

    spec = importlib.util.find_spec(module)
    if spec is not None:  # The real module is available; do nothing.
        return

    parent_name, _, _child = module.rpartition(".")
    if parent_name:
        ensure_optional_dependency_stub(parent_name, extra)
        parent = sys.modules[parent_name]
        if not hasattr(parent, "__path__"):
            parent.__path__ = []  # type: ignore[attr-defined]

    stub = ModuleType(module)
    package_name = module.split(".", 1)[0]

    def _missing_attr(_name: str) -> None:
        raise MissingExtraError(package_name, extra)

    stub.__getattr__ = _missing_attr  # type: ignore[attr-defined]
    stub.__all__ = []  # type: ignore[attr-defined]
    stub.__path__ = []  # type: ignore[attr-defined]
    sys.modules[module] = stub

