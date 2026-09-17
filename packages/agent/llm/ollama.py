from typing import Any

from packages.agent.llm.adapter import ToolSchemaAdapter
from packages.agent.llm.contract import LLMProvider, LLMRequest, LLMResponse
from packages.agent.llm.message_adapter import OllamaMessageAdapter
from packages.domain.config import NexusSettings


class OllamaProvider(LLMProvider):
    def __init__(self, host: str | None = None, model: str | None = None) -> None:
        settings = NexusSettings()
        self._host = host or settings.ollama_host
        self._port = settings.ollama_port
        self._model = model or settings.ollama_model
        self._base_url = f"http://{self._host}:{self._port}"
        self._client: Any = None

    def _ensure_client(self) -> Any:
        if self._client is None:
            import ollama

            self._client = ollama.AsyncClient(host=self._base_url)
        return self._client

    async def generate(self, request: LLMRequest) -> LLMResponse:
        client = self._ensure_client()

        messages = OllamaMessageAdapter.to_ollama_messages(request.messages)
        tools = self._convert_tools(request.tools)

        try:
            response = await client.chat(
                model=self._model,
                messages=messages,
                tools=tools if tools else None,
            )
        except Exception as e:
            raise RuntimeError(f"Ollama request failed: {e}") from e

        return OllamaMessageAdapter.from_ollama_response(response)

    def _convert_tools(self, tool_identifiers: list[str]) -> list[dict[str, Any]]:
        if not tool_identifiers:
            return []
        return ToolSchemaAdapter.to_ollama_tools(
            [self._resolve_tool(tid) for tid in tool_identifiers if self._resolve_tool(tid)]
        )

    def _resolve_tool(self, identifier: str) -> object | None:
        from packages.tools.registry import ToolRegistry

        registry = ToolRegistry()
        return registry.get(identifier)
