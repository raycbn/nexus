from packages.tools.base import Tool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        identifier = tool.get_identifier()
        if identifier in self._tools:
            raise ValueError(f"Tool already registered: {identifier}")
        self._tools[identifier] = tool

    def get(self, identifier: str) -> Tool | None:
        return self._tools.get(identifier)

    def list_tools(self) -> list[Tool]:
        return list(self._tools.values())

    def has(self, identifier: str) -> bool:
        return identifier in self._tools

    def count(self) -> int:
        return len(self._tools)
