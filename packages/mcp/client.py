from typing import Any

from mcp.types import CallToolResult, ListToolsResult
from mcp.types import Tool as MCPTool

from mcp.client import Client as MCPClient
from packages.tools.base import Tool


class MCPToolWrapper(Tool):
    def __init__(self, mcp_tool: MCPTool, client: "MCPToolClient") -> None:
        self._mcp_tool = mcp_tool
        self._client = client

    def get_identifier(self) -> str:
        return self._mcp_tool.name

    def get_name(self) -> str:
        return self._mcp_tool.name

    def get_description(self) -> str:
        return self._mcp_tool.description or ""

    def get_input_schema(self) -> dict[str, Any]:
        return self._mcp_tool.input_schema

    def get_output_schema(self) -> dict[str, Any]:
        return self._mcp_tool.output_schema or {}

    def get_risk_level(self):
        from packages.domain.models.enums import RiskLevel

        return RiskLevel.LOW

    def is_read_only(self) -> bool:
        return True

    def get_required_permissions(self) -> list[str]:
        return ["read"]

    def get_resource_mode(self) -> str:
        meta = self._mcp_tool.meta or {}
        return meta.get("resource_mode", "mcp")

    def get_resource_id(self) -> str | None:
        meta = self._mcp_tool.meta or {}
        return meta.get("resource_id")

    async def execute(self, parameters: dict[str, Any]) -> dict[str, Any]:
        result = await self._client.call_tool(self.get_identifier(), parameters)
        return {
            "content": result.content,
            "structured_content": result.structured_content,
            "is_error": result.is_error,
        }


class MCPToolClient:
    def __init__(self, server_name: str = "nexus") -> None:
        self._server_name = server_name
        self._client: MCPClient | None = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self, server: Any) -> None:
        self._client = MCPClient(server)
        await self._client.__aenter__()
        self._connected = True

    async def disconnect(self) -> None:
        if self._client is not None:
            await self._client.__aexit__(None, None, None)
            self._client = None
            self._connected = False

    async def list_tools(self) -> list[MCPTool]:
        if self._client is None:
            raise RuntimeError("Not connected. Call connect() first.")
        result: ListToolsResult = await self._client.list_tools()
        return result.tools

    async def call_tool(
        self, tool_name: str, arguments: dict[str, Any] | None = None
    ) -> CallToolResult:
        if self._client is None:
            raise RuntimeError("Not connected. Call connect() first.")
        return await self._client.call_tool(tool_name, arguments=arguments or {})

    def discover_tool_metadata(self, tools: list[MCPTool]) -> list[dict[str, Any]]:
        from packages.mcp.adapter import MCPAdapter

        return [MCPAdapter.mcp_tool_to_nexus_metadata(t) for t in tools]

    def create_tool_wrapper(self, mcp_tool: MCPTool) -> MCPToolWrapper:
        return MCPToolWrapper(mcp_tool=mcp_tool, client=self)
