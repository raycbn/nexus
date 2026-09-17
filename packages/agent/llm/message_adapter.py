from typing import Any

from packages.agent.llm.contract import LLMMessage, LLMResponse, ToolCall
from packages.tools.base import Tool


class OllamaMessageAdapter:
    @staticmethod
    def to_ollama_messages(messages: list[LLMMessage]) -> list[dict[str, Any]]:
        ollama_messages: list[dict[str, Any]] = []
        for msg in messages:
            if msg.role == "system":
                ollama_messages.append({"role": "system", "content": msg.content or ""})
            elif msg.role == "user":
                ollama_messages.append({"role": "user", "content": msg.content or ""})
            elif msg.role == "assistant":
                ollama_messages.append(OllamaMessageAdapter._assistant_message(msg))
            elif msg.role == "tool":
                ollama_messages.append(
                    {
                        "role": "tool",
                        "tool_name": msg.tool_name or "",
                        "content": msg.content or "",
                    }
                )
        return ollama_messages

    @staticmethod
    def _assistant_message(msg: LLMMessage) -> dict[str, Any]:
        entry: dict[str, Any] = {"role": "assistant"}
        if msg.content:
            entry["content"] = msg.content
        if msg.tool_calls:
            import json

            entry["tool_calls"] = [
                {
                    "id": tc.id,
                    "function": {
                        "name": tc.tool_name,
                        "arguments": json.dumps(tc.arguments),
                    },
                }
                for tc in msg.tool_calls
            ]
        return entry

    @staticmethod
    def from_ollama_response(
        ollama_response: dict[str, Any], tool_map: dict[str, Tool] | None = None
    ) -> LLMResponse:
        message = ollama_response.get("message", {})
        content = message.get("content", "")

        tool_calls: list[ToolCall] = []
        raw_calls = message.get("tool_calls", [])
        for raw_call in raw_calls:
            function = raw_call.get("function", {})
            arguments_raw = function.get("arguments", "{}")
            try:
                import json

                arguments = json.loads(arguments_raw)
            except (json.JSONDecodeError, TypeError):
                arguments = {"raw": arguments_raw}
            tool_calls.append(
                ToolCall(
                    id=raw_call.get("id", ""),
                    tool_name=function.get("name", ""),
                    arguments=arguments,
                )
            )

        return LLMResponse(content=content, tool_calls=tool_calls)

    @staticmethod
    def tool_result_to_message(tool_call_id: str, tool_name: str, result: str) -> LLMMessage:
        return LLMMessage(
            role="tool",
            tool_name=tool_name,
            content=f"Tool result for {tool_name} (call {tool_call_id}): {result}",
        )
