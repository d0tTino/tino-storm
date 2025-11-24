"""Smoke tests that ensure high-risk modules compile without syntax errors."""

from __future__ import annotations

from pathlib import Path
import py_compile
import tempfile
from typing import Iterable

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Individual files that are historically prone to merge conflicts or syntax
# changes should be explicitly listed so regressions are caught quickly.
CRITICAL_FILES = [
    PROJECT_ROOT / "src/tino_storm/ingest/search.py",
    PROJECT_ROOT / "src/tino_storm/providers/multi_source.py",
]

# Directories with a large surface area of provider/ingestion logic are
# considered high-risk. We walk each directory recursively and compile every
# Python module in isolation so that syntax errors fail fast.
HIGH_RISK_DIRECTORIES = [
    PROJECT_ROOT / "src/tino_storm/ingest",
    PROJECT_ROOT / "src/tino_storm/ingestion",
    PROJECT_ROOT / "src/tino_storm/providers",
    PROJECT_ROOT / "src/tino_storm/retrieval",
    PROJECT_ROOT / "src/tino_storm/skills",
]


def _iter_modules(target: Path) -> Iterable[Path]:
    if target.is_file():
        yield target
        return

    for path in sorted(target.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        yield path


def _compile_paths(paths: Iterable[Path]) -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory() as build_dir:
        build_dir_path = Path(build_dir)
        for path in paths:
            pyc_target = build_dir_path / f"{path.stem}.pyc"
            try:
                py_compile.compile(
                    str(path),
                    cfile=str(pyc_target),
                    doraise=True,
                )
            except py_compile.PyCompileError as exc:
                errors.append(f"{path.relative_to(PROJECT_ROOT)}: {exc.msg}")
            except Exception as exc:  # pragma: no cover - defensive
                errors.append(f"{path.relative_to(PROJECT_ROOT)}: {exc}")
    return errors


@pytest.mark.parametrize(
    "target",
    CRITICAL_FILES + HIGH_RISK_DIRECTORIES,
    ids=lambda path: str(path.relative_to(PROJECT_ROOT)),
)
def test_compile_smoke(target: Path) -> None:
    assert target.exists(), f"Smoke target missing: {target}"
    errors = _compile_paths(_iter_modules(target))
    if errors:
        formatted = "\n".join(f"  - {error}" for error in errors)
        pytest.fail(f"Syntax errors detected during smoke compilation:\n{formatted}")
