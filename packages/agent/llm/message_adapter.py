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
                        "tool_call_id": msg.tool_call_id or "",
                        "name": msg.tool_name or "",
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
    def _sanitize_content(content: str) -> str:
        import re

        thinking_pattern = re.compile(r"<\|thinking_start\|>.*?<\|thinking_end\|>", re.DOTALL)
        content = thinking_pattern.sub("", content)

        # Use regex to find end-think markers flexibly
        # Pattern matches: END + optional ZWSP + THINK, or <|end_think|>, or TODO
        # Note: \u200b in regular string = ZWSP character (U+200B)
        end_think_pattern = re.compile(r"(?:END\u200b?THINK|<\|end_think_\|>|TODO)")
        match = end_think_pattern.search(content)
        if match:
            return content[match.end() :].strip()
        else:
            return content.strip()

    @staticmethod
    def from_ollama_response(
        ollama_response: dict[str, Any], tool_map: dict[str, Tool] | None = None
    ) -> LLMResponse:
        message = ollama_response.get("message", {})
        raw_content = message.get("content", "")
        thinking = message.get("thinking") or ""

        content = OllamaMessageAdapter._sanitize_content(raw_content)

        tool_calls: list[ToolCall] = []
        raw_calls = message.get("tool_calls") or []
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

        return LLMResponse(content=content, tool_calls=tool_calls, thinking=thinking)

    @staticmethod
    def tool_result_to_message(tool_call_id: str, tool_name: str, result: str) -> LLMMessage:
        return LLMMessage(
            role="tool",
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            content=f"Tool result for {tool_name} (call {tool_call_id}): {result}",
        )
