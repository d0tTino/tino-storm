#!/usr/bin/env python3
"""Guard against source drift between canonical and legacy module trees."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class DuplicateTreeRule:
    legacy_root: Path
    canonical_root: Path


RULES = [
    DuplicateTreeRule(
        legacy_root=REPO_ROOT / "knowledge_storm",
        canonical_root=REPO_ROOT / "src" / "tino_storm",
    )
]


def _is_thin_forwarder(file_path: Path) -> bool:
    source = file_path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False

    import_count = 0
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(getattr(node, "value", None), ast.Constant) and isinstance(node.value.value, str):
            continue
        if isinstance(node, ast.ImportFrom):
            if node.level != 0 or not node.module or not node.module.startswith("tino_storm"):
                return False
            import_count += 1
            continue
        return False

    return import_count >= 1


def _collect_violations(rule: DuplicateTreeRule) -> list[str]:
    violations: list[str] = []
    for legacy_file in sorted(rule.legacy_root.rglob("*.py")):
        if "__pycache__" in legacy_file.parts:
            continue
        relative = legacy_file.relative_to(rule.legacy_root)
        if relative == Path("__init__.py"):
            continue
        canonical_file = rule.canonical_root / relative
        if not canonical_file.exists():
            continue
        if not _is_thin_forwarder(legacy_file):
            violations.append(
                f"{legacy_file.relative_to(REPO_ROOT)} duplicates {canonical_file.relative_to(REPO_ROOT)} but is not a thin forwarder"
            )
    return violations


def main() -> int:
    all_violations: list[str] = []
    for rule in RULES:
        all_violations.extend(_collect_violations(rule))

    if all_violations:
        print("Duplicate module drift detected:")
        for violation in all_violations:
            print(f" - {violation}")
        return 1

    print("Duplicate module guard passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
