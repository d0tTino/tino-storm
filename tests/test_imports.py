import importlib
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))
sys.path.insert(0, str(ROOT_DIR))


def test_modules_available():
    assert importlib.import_module("knowledge_storm") is not None
    assert importlib.import_module("tino_storm") is not None
