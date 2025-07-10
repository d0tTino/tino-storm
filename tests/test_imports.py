import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_modules_available():
    assert importlib.import_module("knowledge_storm") is not None
    assert importlib.import_module("tino_storm") is not None
