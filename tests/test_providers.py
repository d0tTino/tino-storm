import pytest

from tino_storm.providers import get_llm, get_retriever
from knowledge_storm.lm import OpenAIModel
from knowledge_storm.rm import YouRM


def test_get_llm_valid():
    assert get_llm("openai") is OpenAIModel


def test_get_llm_invalid():
    with pytest.raises(ValueError):
        get_llm("unknown")


def test_get_retriever_valid():
    assert get_retriever("you") is YouRM


def test_get_retriever_invalid():
    with pytest.raises(ValueError):
        get_retriever("unknown")
