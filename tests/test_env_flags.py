"""SAMPLE_MODE / USE_ZETARIS truthiness must be parsed identically everywhere (true, 1, yes, on)."""
import pytest

from app.envutil import env_bool


@pytest.mark.parametrize("raw", ["true", "TRUE", "True", "1", "yes", "on", " true "])
def test_env_bool_truthy(monkeypatch, raw):
    monkeypatch.setenv("MT_FLAG", raw)
    assert env_bool("MT_FLAG") is True


@pytest.mark.parametrize("raw", ["false", "0", "no", "off", "", "banana"])
def test_env_bool_falsy(monkeypatch, raw):
    monkeypatch.setenv("MT_FLAG", raw)
    assert env_bool("MT_FLAG") is False


def test_env_bool_default_when_unset(monkeypatch):
    monkeypatch.delenv("MT_FLAG", raising=False)
    assert env_bool("MT_FLAG") is False
    assert env_bool("MT_FLAG", default=True) is True


def test_sample_mode_one_is_honoured_by_llm_client(monkeypatch):
    """Regression: SAMPLE_MODE=1 used to be accepted by DataStore but ignored by LLMClient (RuntimeError on first call)."""
    from app.adapters.llm_client import LLMClient

    monkeypatch.setenv("SAMPLE_MODE", "1")
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    monkeypatch.delenv("METERLESS_RUNTIME_TOKEN", raising=False)
    client = LLMClient()
    assert client.sample_mode is True
    res = client.generate("hello")
    assert res["fallback"] is True or res.get("llm_used") is False


def test_sample_mode_one_is_honoured_by_datastore(monkeypatch):
    from app.adapters.data_store import DataStore

    monkeypatch.setenv("SAMPLE_MODE", "1")
    monkeypatch.setenv("USE_ZETARIS", "true")
    assert DataStore().use_zetaris is False  # sample mode wins
