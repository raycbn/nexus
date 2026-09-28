import sys
import time
from typing import Any

from packages.agent.llm.adapter import ToolSchemaAdapter
from packages.agent.llm.contract import LLMProvider, LLMRequest, LLMResponse
from packages.agent.llm.message_adapter import OllamaMessageAdapter
from packages.domain.config import NexusSettings
from packages.tools.registry import ToolRegistry


class OllamaProvider(LLMProvider):
    def __init__(
        self,
        host: str | None = None,
        model: str | None = None,
        registry: ToolRegistry | None = None,
        timeout: int | None = None,
        num_predict: int | None = None,
    ) -> None:
        settings = NexusSettings()
        self._host = host or settings.ollama_host
        self._port = settings.ollama_port
        self._model = model or settings.ollama_model
        self._registry = registry
        self._think: bool | str = settings.ollama_think
        self._num_ctx: int = settings.ollama_num_ctx
        self._num_predict: int | None = num_predict
        self._timeout: int = timeout or settings.ollama_timeout
        if self._model is None:
            raise RuntimeError(
                "OLLAMA_MODEL environment variable is not configured. "
                "Set it to a chat-capable model (e.g. hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M) "
                "and ensure it is loaded in Ollama."
            )
        self._base_url = f"http://{self._host}:{self._port}"
        self._client: Any = None

    def _ensure_client(self) -> Any:
        if self._client is None:
            import ollama

            self._client = ollama.AsyncClient(
                host=self._base_url,
                timeout=self._timeout,
            )
        return self._client

    async def generate(self, request: LLMRequest) -> LLMResponse:
        client = self._ensure_client()

        messages = OllamaMessageAdapter.to_ollama_messages(request.messages)
        tools = self._convert_tools(request.tools)
        think = self._think
        options = {"num_ctx": self._num_ctx}
        if self._num_predict is not None:
            options["num_predict"] = self._num_predict

        print("[LLM] Sending request...")
        print(f"[LLM] Model: {self._model}")
        print(f"[LLM] Tools: {len(tools)}")
        llm_start = time.perf_counter()

        try:
            response = await client.chat(
                model=self._model,
                messages=messages,
                tools=tools if tools else None,
                think=think,
                format=request.response_format,
                options=options,
            )
            llm_duration = time.perf_counter() - llm_start
        except Exception as e:
            print(
                f"[LLM] Request failed: {type(e).__name__}: {e!r}",
                file=sys.stderr,
            )
            raise RuntimeError(f"Ollama request failed: {e}") from e

        print(f"[LLM] Response received in {llm_duration:.3f}s")
        if hasattr(response, "model_dump"):
            response_payload = response.model_dump()
        elif isinstance(response, dict):
            response_payload = response
        else:
            raise RuntimeError(f"Unsupported Ollama response type: {type(response).__name__}")

        result = OllamaMessageAdapter.from_ollama_response(response_payload)
        return result

    def _convert_tools(self, tool_identifiers: list[str]) -> list[dict[str, Any]]:
        if not tool_identifiers:
            return []
        return ToolSchemaAdapter.to_ollama_tools(
            [self._resolve_tool(tid) for tid in tool_identifiers if self._resolve_tool(tid)]
        )

    def _resolve_tool(self, identifier: str) -> object | None:
        if self._registry is not None:
            return self._registry.get(identifier)
        from packages.tools.registry import ToolRegistry

        registry = ToolRegistry()
        return registry.get(identifier)
