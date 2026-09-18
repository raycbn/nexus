import pytest
from packages.domain.config import NexusSettings


def test_ollama_host_default():
    settings = NexusSettings()
    assert settings.ollama_host == "127.0.0.1"


def test_ollama_port_default():
    settings = NexusSettings()
    assert settings.ollama_port == 11434


def test_ollama_model_default():
    settings = NexusSettings()
    if settings.ollama_model is not None:
        pytest.skip("OLLAMA_MODEL is configured; skip default test")
    assert settings.ollama_model is None


def test_ollama_think_default():
    settings = NexusSettings()
    assert settings.ollama_think is False


def test_ollama_num_ctx_default():
    settings = NexusSettings()
    assert settings.ollama_num_ctx == 8192


def test_ollama_timeout_default():
    settings = NexusSettings()
    assert settings.ollama_timeout == 120


def test_ollama_base_url_from_host():
    settings = NexusSettings()
    settings.ollama_host = "127.0.0.1"
    settings.ollama_port = 11434
    assert settings.ollama_base_url == "http://127.0.0.1:11434"
