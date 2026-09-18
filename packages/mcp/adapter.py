from typing import Any

from mcp.types import CallToolRequestParams, CallToolResult, TextContent
from mcp.types import Tool as MCPTool

from packages.tools.base import Tool


class MCPAdapter:
    @staticmethod
    def nexus_to_mcp_tool(tool: Tool) -> MCPTool:
        return MCPTool(
            name=tool.get_identifier(),
            description=tool.get_description(),
            input_schema=tool.get_input_schema(),
            output_schema=tool.get_output_schema(),
        )

    @staticmethod
    def nexus_tools_to_mcp_tools(tools: list[Tool]) -> list[MCPTool]:
        return [MCPAdapter.nexus_to_mcp_tool(t) for t in tools]

    @staticmethod
    def mcp_tool_to_nexus_metadata(tool: MCPTool) -> dict[str, Any]:
        return {
            "identifier": tool.name,
            "name": tool.name,
            "description": tool.description or "",
            "input_schema": tool.input_schema,
            "output_schema": tool.output_schema or {},
            "mcp_tool": True,
        }

    @staticmethod
    def mcp_call_params(tool_name: str, arguments: dict[str, Any]) -> CallToolRequestParams:
        return CallToolRequestParams(name=tool_name, arguments=arguments)

    @staticmethod
    def mcp_call_result_to_dict(result: CallToolResult) -> dict[str, Any]:
        content_texts = []
        structured = result.structured_content
        if result.content:
            for item in result.content:
                if isinstance(item, TextContent) and item.text:
                    content_texts.append(item.text)
        return {
            "content": "\n".join(content_texts),
            "structured_content": structured,
            "is_error": result.is_error,
        }
