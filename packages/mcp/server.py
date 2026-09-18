from typing import Any

from mcp.types import (
    CallToolRequestParams,
    CallToolResult,
    ListToolsResult,
    TextContent,
)
from mcp.types import (
    Tool as MCPTool,
)

from mcp.server import Server
from packages.tools.registry import ToolRegistry


class NexusMCPServer:
    def __init__(
        self,
        name: str = "nexus",
        version: str = "0.1.0",
        registry: ToolRegistry | None = None,
    ) -> None:
        self._registry = registry or ToolRegistry()
        self._server = Server(
            name=name,
            version=version,
            on_list_tools=self._on_list_tools,
            on_call_tool=self._on_call_tool,
        )

    @property
    def server(self) -> Server:
        return self._server

    async def _on_list_tools(self, session: Any, params: Any | None) -> ListToolsResult:
        tools = self._registry.list_tools()
        mcp_tools: list[MCPTool] = []
        for tool in tools:
            mcp_tools.append(
                MCPTool(
                    name=tool.get_identifier(),
                    description=tool.get_description(),
                    input_schema=tool.get_input_schema(),
                    output_schema=tool.get_output_schema(),
                    meta={
                        "resource_mode": tool.get_resource_mode(),
                        "resource_id": tool.get_resource_id(),
                    },
                )
            )
        return ListToolsResult(tools=mcp_tools)

    async def _on_call_tool(self, session: Any, params: CallToolRequestParams) -> CallToolResult:
        tool = self._registry.get(params.name)
        if tool is None:
            return CallToolResult(
                content=[TextContent(text=f"Error: Unknown tool: {params.name}")],
                is_error=True,
            )

        try:
            result = await tool.execute(params.arguments or {})
            return CallToolResult(
                content=[TextContent(text=str(result))],
                structured_content=result if isinstance(result, dict) else {},
                is_error=False,
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(text=f"Error: {e}")],
                structured_content={},
                is_error=True,
            )
