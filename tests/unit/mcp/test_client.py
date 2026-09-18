import asyncio

import pytest
from packages.mcp.client import MCPToolClient, MCPToolWrapper
from packages.mcp.server import NexusMCPServer
from packages.tools.providers.mock_tools import GetSystemInfoTool
from packages.tools.registry import ToolRegistry


@pytest.mark.asyncio
async def test_client_connect_disconnect():
    registry = ToolRegistry()
    registry.register(GetSystemInfoTool())
    server = NexusMCPServer(name="test", version="1.0", registry=registry)
    client = MCPToolClient(server_name="test")

    await client.connect(server.server)
    assert client.is_connected is True

    await client.disconnect()
    assert client.is_connected is False


@pytest.mark.asyncio
async def test_client_list_tools():
    registry = ToolRegistry()
    registry.register(GetSystemInfoTool())
    server = NexusMCPServer(name="test", version="1.0", registry=registry)
    client = MCPToolClient(server_name="test")

    await client.connect(server.server)
    tools = await client.list_tools()
    assert len(tools) == 1
    assert tools[0].name == "get_system_info"

    await client.disconnect()


@pytest.mark.asyncio
async def test_client_call_tool():
    registry = ToolRegistry()
    registry.register(GetSystemInfoTool())
    server = NexusMCPServer(name="test", version="1.0", registry=registry)
    client = MCPToolClient(server_name="test")

    await client.connect(server.server)
    result = await client.call_tool("get_system_info", {"target": "test"})
    assert result.is_error is False

    await client.disconnect()


def test_client_raises_when_not_connected():
    client = MCPToolClient(server_name="test")
    with pytest.raises(RuntimeError):
        asyncio.run(client.list_tools())


@pytest.mark.asyncio
async def test_client_discover_tool_metadata():
    registry = ToolRegistry()
    registry.register(GetSystemInfoTool())
    server = NexusMCPServer(name="test", version="1.0", registry=registry)
    client = MCPToolClient(server_name="test")

    await client.connect(server.server)
    tools = await client.list_tools()
    metadata = client.discover_tool_metadata(tools)
    assert len(metadata) == 1
    assert metadata[0]["identifier"] == "get_system_info"
    assert metadata[0]["mcp_tool"] is True

    await client.disconnect()


def test_client_create_tool_wrapper():
    from mcp.types import Tool as MCPTool

    client = MCPToolClient(server_name="test")
    mcp_tool = MCPTool(name="test_tool", description="test", inputSchema={})
    wrapper = client.create_tool_wrapper(mcp_tool)
    assert isinstance(wrapper, MCPToolWrapper)
    assert wrapper.get_identifier() == "test_tool"
