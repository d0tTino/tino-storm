import pytest

from tino_storm.search import _resolve_provider, ResearchError


def test_resolve_provider_raises_on_malformed_spec():
    spec = "malformed-spec"
    with pytest.raises(ResearchError) as exc:
        _resolve_provider(spec)
    assert exc.value.provider_spec == spec
    assert f"Failed to load provider '{spec}'" in str(exc.value)


def test_resolve_provider_env_uses_spec(monkeypatch):
    spec = "anotherbad"
    monkeypatch.setenv("STORM_SEARCH_PROVIDER", spec)
    with pytest.raises(ResearchError) as exc:
        _resolve_provider(None)
    assert exc.value.provider_spec == spec
    assert f"Failed to load provider '{spec}'" in str(exc.value)
