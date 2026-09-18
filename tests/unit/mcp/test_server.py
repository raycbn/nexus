import pytest
from packages.mcp.server import NexusMCPServer
from packages.tools.providers.mock_tools import GetSystemInfoTool
from packages.tools.registry import ToolRegistry


def test_server_creation():
    server = NexusMCPServer(name="test", version="1.0")
    assert server.server is not None
    assert server.server.name == "test"
    assert server.server.version == "1.0"


def test_server_with_registry():
    registry = ToolRegistry()
    registry.register(GetSystemInfoTool())
    server = NexusMCPServer(name="test", version="1.0", registry=registry)
    assert server.server is not None


@pytest.mark.asyncio
async def test_server_lists_tools():
    registry = ToolRegistry()
    registry.register(GetSystemInfoTool())
    server = NexusMCPServer(name="test", version="1.0", registry=registry)

    result = await server._on_list_tools(session=None, params=None)
    assert len(result.tools) == 1
    assert result.tools[0].name == "get_system_info"


@pytest.mark.asyncio
async def test_server_calls_tool():
    registry = ToolRegistry()
    registry.register(GetSystemInfoTool())
    server = NexusMCPServer(name="test", version="1.0", registry=registry)

    from mcp.types import CallToolRequestParams

    params = CallToolRequestParams(name="get_system_info", arguments={"target": "test"})
    result = await server._on_call_tool(session=None, params=params)
    assert result.is_error is False


@pytest.mark.asyncio
async def test_server_unknown_tool():
    server = NexusMCPServer(name="test", version="1.0")

    from mcp.types import CallToolRequestParams

    params = CallToolRequestParams(name="unknown", arguments={})
    result = await server._on_call_tool(session=None, params=params)
    assert result.is_error is True


@pytest.mark.asyncio
async def test_server_tool_execution_failure():
    class FailingTool:
        def get_identifier(self):
            return "failing"

        def get_name(self):
            return "Failing"

        def get_description(self):
            return ""

        def get_input_schema(self):
            return {}

        def get_output_schema(self):
            return {}

        def get_risk_level(self):
            from packages.domain.models.enums import RiskLevel

            return RiskLevel.LOW

        def is_read_only(self):
            return True

        def get_required_permissions(self):
            return []

        def get_resource_mode(self):
            return "simulation"

        async def execute(self, parameters):
            raise RuntimeError("intentional failure")

    registry = ToolRegistry()
    registry.register(FailingTool())
    server = NexusMCPServer(name="test", version="1.0", registry=registry)

    from mcp.types import CallToolRequestParams

    params = CallToolRequestParams(name="failing", arguments={})
    result = await server._on_call_tool(session=None, params=params)
    assert result.is_error is True
