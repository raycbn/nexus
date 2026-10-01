import json
from typing import Any

import httpx

from packages.agent.llm.adapter import ToolSchemaAdapter
from packages.agent.llm.contract import (
    LLMProvider,
    LLMProviderError,
    LLMRateLimitError,
    LLMRequest,
    LLMResponse,
    ToolCall,
)
from packages.agent.llm.message_adapter import OllamaMessageAdapter
from packages.tools.registry import ToolRegistry


class OpenAICompatibleProvider(LLMProvider):
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        registry: ToolRegistry | None = None,
        timeout: int = 120,
    ) -> None:
        self._endpoint = base_url.rstrip("/") + "/chat/completions"
        self._api_key = api_key
        self._model = model
        self._registry = registry
        self._timeout = timeout

    async def generate(self, request: LLMRequest) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": OllamaMessageAdapter.to_ollama_messages(request.messages),
        }
        tools = self._convert_tools(request.tools)
        if tools:
            payload["tools"] = tools
        if request.response_format is not None:
            payload["response_format"] = request.response_format

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(self._endpoint, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                retry_after = self._retry_after(exc.response)
                raise LLMRateLimitError(
                    f"Provider rate limit reached for model {self._model}",
                    retry_after=retry_after,
                ) from exc
            raise LLMProviderError(
                f"Provider request failed with HTTP {exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMProviderError("Provider request failed") from exc

        return self._parse_response(data)

    @staticmethod
    def _retry_after(response: httpx.Response) -> float | None:
        value = response.headers.get("Retry-After")
        if value is None:
            return None
        try:
            return float(value)
        except ValueError:
            return None

    def _convert_tools(self, tool_identifiers: list[str]) -> list[dict[str, Any]]:
        if not tool_identifiers:
            return []
        tools: list[object] = []
        for identifier in tool_identifiers:
            tool = self._resolve_tool(identifier)
            if tool is not None:
                tools.append(tool)
        return ToolSchemaAdapter.to_ollama_tools(tools)

    def _resolve_tool(self, identifier: str) -> object | None:
        if self._registry is not None:
            return self._registry.get(identifier)
        return ToolRegistry().get(identifier)

    @staticmethod
    def _parse_response(data: dict[str, Any]) -> LLMResponse:
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("OpenAI-compatible provider returned no choices")
        message = choices[0].get("message") or {}
        raw_calls = message.get("tool_calls") or []
        tool_calls: list[ToolCall] = []
        for raw_call in raw_calls:
            function = raw_call.get("function") or {}
            raw_arguments = function.get("arguments", "{}")
            try:
                arguments = (
                    json.loads(raw_arguments)
                    if isinstance(raw_arguments, str)
                    else raw_arguments
                )
            except (json.JSONDecodeError, TypeError):
                arguments = {"raw": raw_arguments}
            tool_calls.append(
                ToolCall(
                    id=raw_call.get("id", ""),
                    tool_name=function.get("name", ""),
                    arguments=arguments,
                )
            )

        thinking = message.get("reasoning") or message.get("thinking") or ""
        return LLMResponse(
            content=message.get("content") or "",
            tool_calls=tool_calls,
            thinking=thinking,
        )
