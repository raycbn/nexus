from packages.mcp.adapter import MCPAdapter
from packages.tools.providers.mock_tools import GetSystemInfoTool


def test_nexus_to_mcp_tool():
    tool = GetSystemInfoTool()
    mcp_tool = MCPAdapter.nexus_to_mcp_tool(tool)
    assert mcp_tool.name == "get_system_info"
    assert mcp_tool.description == "Returns system information for a target resource"
    assert mcp_tool.input_schema == {"type": "object", "properties": {"target": {"type": "string"}}}


def test_nexus_tools_to_mcp_tools():
    tools = [GetSystemInfoTool(), GetSystemInfoTool()]
    mcp_tools = MCPAdapter.nexus_tools_to_mcp_tools(tools)
    assert len(mcp_tools) == 2
    assert all(t.name == "get_system_info" for t in mcp_tools)


def test_mcp_tool_to_nexus_metadata():
    mcp_tool = GetSystemInfoTool()
    from mcp.types import Tool as MCPTool

    mcp_def = MCPTool(
        name=mcp_tool.get_identifier(),
        description=mcp_tool.get_description(),
        input_schema=mcp_tool.get_input_schema(),
    )
    metadata = MCPAdapter.mcp_tool_to_nexus_metadata(mcp_def)
    assert metadata["identifier"] == "get_system_info"
    assert metadata["name"] == "get_system_info"
    assert metadata["mcp_tool"] is True
    assert metadata["input_schema"] == {
        "type": "object",
        "properties": {"target": {"type": "string"}},
    }


def test_mcp_call_params():
    params = MCPAdapter.mcp_call_params("get_system_info", {"target": "server1"})
    assert params.name == "get_system_info"
    assert params.arguments == {"target": "server1"}


def test_mcp_call_result_to_dict():

    result = call_tool_result_mock()
    d = MCPAdapter.mcp_call_result_to_dict(result)
    assert d["content"] == "test result"
    assert d["is_error"] is False


def call_tool_result_mock():
    from mcp.types import CallToolResult, TextContent

    return CallToolResult(content=[TextContent(text="test result")])
