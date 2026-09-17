from typing import Any

from packages.tools.base import Tool


class ToolSchemaAdapter:
    @staticmethod
    def to_ollama_tool(tool: Tool) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": tool.get_identifier(),
                "description": tool.get_description(),
                "parameters": tool.get_input_schema(),
            },
        }

    @staticmethod
    def to_ollama_tools(tools: list[Tool]) -> list[dict[str, Any]]:
        return [ToolSchemaAdapter.to_ollama_tool(t) for t in tools]
