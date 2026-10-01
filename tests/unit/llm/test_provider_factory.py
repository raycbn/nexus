import pytest
from packages.agent.llm.catalog import AIProvider
from packages.agent.llm.gemini import GeminiProvider
from packages.agent.llm.ollama import OllamaProvider
from packages.agent.llm.openai_compatible import OpenAICompatibleProvider
from packages.agent.llm.provider_factory import (
    OPENAI_COMPATIBLE_BASE_URLS,
    ProviderConfig,
    create_provider,
)


def test_creates_bundled_ollama_provider() -> None:
    provider = create_provider(ProviderConfig(AIProvider.OLLAMA, "qwen3:1.7b"))
    assert isinstance(provider, OllamaProvider)


def test_creates_openrouter_compatible_provider() -> None:
    provider = create_provider(
        ProviderConfig(AIProvider.OPENROUTER, "openrouter/free", api_key="test-key")
    )
    assert isinstance(provider, OpenAICompatibleProvider)


def test_creates_gemini_provider() -> None:
    provider = create_provider(
        ProviderConfig(AIProvider.GEMINI, "gemini-3.8-flash", api_key="test-key")
    )
    assert isinstance(provider, GeminiProvider)


def test_gemini_provider_requires_api_key() -> None:
    with pytest.raises(ValueError, match="API key required for gemini"):
        create_provider(ProviderConfig(AIProvider.GEMINI, "gemini-3.8-flash"))


def test_compatible_provider_uses_known_endpoint() -> None:
    config = ProviderConfig(AIProvider.GROQ, "openai/gpt-oss-120b", api_key="test-key")
    assert OPENAI_COMPATIBLE_BASE_URLS[config.provider] == "https://api.groq.com/openai/v1"


def test_external_provider_requires_api_key() -> None:
    with pytest.raises(ValueError, match="API key required"):
        create_provider(ProviderConfig(AIProvider.CEREBRAS, "gpt-oss-120b"))


def test_unimplemented_specific_provider_is_explicit() -> None:
    with pytest.raises(NotImplementedError, match="anthropic"):
        create_provider(ProviderConfig(AIProvider.ANTHROPIC, "claude", api_key="test-key"))


def test_custom_openai_compatible_provider_accepts_custom_base_url() -> None:
    provider = create_provider(
        ProviderConfig(
            AIProvider.OPENAI_COMPATIBLE,
            "custom-model",
            api_key="test-key",
            base_url="https://example.test/v1",
        )
    )
    assert isinstance(provider, OpenAICompatibleProvider)


def test_gemini_uses_its_native_adapter_even_with_custom_base_url() -> None:
    provider = create_provider(
        ProviderConfig(
            AIProvider.GEMINI,
            "gemini-3.8-flash",
            api_key="test-key",
            base_url="https://example.test/v1",
        )
    )
    assert isinstance(provider, GeminiProvider)
