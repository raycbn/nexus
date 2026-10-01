from typing import Any

import httpx

from packages.agent.llm.contract import LLMRequest, LLMResponse
from packages.agent.llm.openai_compatible import OpenAICompatibleProvider

GEMINI_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
GEMINI_MODELS_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


class GeminiProvider(OpenAICompatibleProvider):
    """Gemini adapter using Google's official OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3.8-flash",
        registry=None,
        timeout: int = 120,
    ) -> None:
        super().__init__(
            base_url=GEMINI_OPENAI_BASE_URL,
            api_key=api_key,
            model=model,
            registry=registry,
            timeout=timeout,
        )

    async def health_check(self) -> bool:
        """Verify that the configured Gemini model is reachable with this key."""
        url = f"{GEMINI_MODELS_BASE_URL}/models/{self._model}"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(url, headers={"x-goog-api-key": self._api_key})
        return response.is_success

    async def detect_capabilities(self) -> dict[str, Any]:
        """Return provider metadata plus capabilities advertised by the model."""
        url = f"{GEMINI_MODELS_BASE_URL}/models/{self._model}"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(url, headers={"x-goog-api-key": self._api_key})
            response.raise_for_status()
            model = response.json()

        return {
            "provider": "gemini",
            "model": self._model,
            "available": True,
            "tool_calling": True,
            "reasoning": True,
            "structured_output": True,
            "context_window_tokens": model.get("inputTokenLimit"),
            "output_token_limit": model.get("outputTokenLimit"),
            "supported_generation_methods": model.get("supportedGenerationMethods", []),
        }

    async def generate(self, request: LLMRequest) -> LLMResponse:
        normalized = request
        if request.response_format == "json":
            normalized = request.model_copy(
                update={"response_format": {"type": "json_object"}}
            )
        return await super().generate(normalized)
