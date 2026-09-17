from packages.agent.llm.contract import LLMMessage
from packages.agent.llm.ollama import OllamaProvider


def test_ollama_provider_has_host_and_model():
    provider = OllamaProvider(host="localhost", model="test-model")
    assert provider._host == "localhost"
    assert provider._model == "test-model"
    assert provider._base_url == "http://localhost:11434"


def test_ollama_provider_uses_settings_by_default():
    provider = OllamaProvider()
    assert provider._host == "localhost"
    assert provider._model == "nomic-embed-text"


def test_ollama_provider_request_conversion():
    _ = OllamaProvider()
    _ = LLMMessage(role="user", content="Hello")
