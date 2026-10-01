from dataclasses import dataclass

from packages.agent.llm.catalog import AIProvider
from packages.agent.llm.contract import LLMProvider
from packages.agent.llm.gemini import GeminiProvider
from packages.agent.llm.ollama import OllamaProvider
from packages.agent.llm.openai_compatible import OpenAICompatibleProvider
from packages.tools.registry import ToolRegistry


@dataclass(frozen=True)
class ProviderConfig:
    provider: AIProvider
    model: str
    api_key: str | None = None
    base_url: str | None = None
    timeout: int = 120
    num_predict: int | None = None


OPENAI_COMPATIBLE_BASE_URLS: dict[AIProvider, str] = {
    AIProvider.OPENROUTER: "https://openrouter.ai/api/v1",
    AIProvider.GROQ: "https://api.groq.com/openai/v1",
    AIProvider.CEREBRAS: "https://api.cerebras.ai/v1",
    AIProvider.NVIDIA: "https://integrate.api.nvidia.com/v1",
}

SUPPORTED_RUNTIME_PROVIDERS = frozenset({
    AIProvider.OLLAMA,
    AIProvider.GEMINI,
    *OPENAI_COMPATIBLE_BASE_URLS.keys(),
    AIProvider.OPENAI_COMPATIBLE,
})


def create_provider(
    config: ProviderConfig,
    registry: ToolRegistry | None = None,
) -> LLMProvider:
    if config.provider is AIProvider.OLLAMA:
        return OllamaProvider(
            host=config.base_url or "127.0.0.1",
            model=config.model,
            registry=registry,
            timeout=config.timeout,
            num_predict=config.num_predict,
        )

    if config.provider is AIProvider.GEMINI:
        if not config.api_key:
            raise ValueError("API key required for gemini")
        return GeminiProvider(
            api_key=config.api_key,
            model=config.model,
            registry=registry,
            timeout=config.timeout,
        )

    compatible_provider = config.provider in OPENAI_COMPATIBLE_BASE_URLS
    custom_compatible = (
        config.provider is AIProvider.OPENAI_COMPATIBLE and config.base_url is not None
    )
    if compatible_provider or custom_compatible:
        if not config.api_key:
            raise ValueError(f"API key required for {config.provider.value}")
        base_url = config.base_url or OPENAI_COMPATIBLE_BASE_URLS[config.provider]
        return OpenAICompatibleProvider(
            base_url=base_url,
            api_key=config.api_key,
            model=config.model,
            registry=registry,
            timeout=config.timeout,
        )

    raise NotImplementedError(
        f"No runtime adapter registered for provider {config.provider.value}"
    )
