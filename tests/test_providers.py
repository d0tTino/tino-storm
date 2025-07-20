import pytest

from tino_storm.providers import get_llm, get_retriever
from knowledge_storm.lm import OpenAIModel, VLLMClient
from knowledge_storm.rm import YouRM
from tino_storm.rrf import RRFRetriever


def test_get_llm_valid():
    assert get_llm("openai") is OpenAIModel


def test_get_llm_invalid():
    with pytest.raises(ValueError):
        get_llm("unknown")


def test_get_retriever_valid():
    assert get_retriever("you") is YouRM


def test_get_rrf_retriever_valid():
    assert get_retriever("rrf") is RRFRetriever


def test_get_retriever_invalid():
    with pytest.raises(ValueError):
        get_retriever("unknown")


def test_get_llm_cloud_disallowed(monkeypatch):
    monkeypatch.setenv("STORM_CLOUD_ALLOWED", "false")
    with pytest.raises(ValueError):
        get_llm("openai")


def test_get_llm_non_cloud_allowed(monkeypatch):
    monkeypatch.setenv("STORM_CLOUD_ALLOWED", "false")
    assert get_llm("vllm") is VLLMClient
