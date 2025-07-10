import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_modules_available():
    assert importlib.util.find_spec("knowledge_storm") is not None
    assert importlib.util.find_spec("tino_storm") is not None
