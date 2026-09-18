import uuid
from datetime import datetime

from packages.mcp.events import (
    MCPConnectedEvent,
    MCPDisconnectedEvent,
    MCPToolCallCompletedEvent,
    MCPToolCallFailedEvent,
    MCPToolCallStartedEvent,
    MCPToolDiscoveredEvent,
)


def test_mcp_connected_event():
    event = MCPConnectedEvent(
        client_id=uuid.uuid4(),
        server_name="test",
        server_version="1.0",
        transport="in-process",
    )
    assert event.server_name == "test"
    assert event.transport == "in-process"
    assert isinstance(event.timestamp, datetime)


def test_mcp_disconnected_event():
    event = MCPDisconnectedEvent(
        client_id=uuid.uuid4(),
        reason="user_initiated",
    )
    assert event.reason == "user_initiated"


def test_mcp_tool_discovered_event():
    event = MCPToolDiscoveredEvent(
        client_id=uuid.uuid4(),
        tool_name="get_system_info",
        tool_description="Returns system info",
    )
    assert event.tool_name == "get_system_info"
    assert event.tool_description == "Returns system info"


def test_mcp_tool_call_started_event():
    event = MCPToolCallStartedEvent(
        client_id=uuid.uuid4(),
        tool_name="get_system_info",
        arguments={"target": "test"},
    )
    assert event.tool_name == "get_system_info"
    assert event.arguments == {"target": "test"}


def test_mcp_tool_call_completed_event():
    event = MCPToolCallCompletedEvent(
        client_id=uuid.uuid4(),
        tool_name="get_system_info",
        result={"hostname": "test"},
        duration=0.5,
    )
    assert event.result == {"hostname": "test"}
    assert event.duration == 0.5


def test_mcp_tool_call_failed_event():
    event = MCPToolCallFailedEvent(
        client_id=uuid.uuid4(),
        tool_name="get_system_info",
        error="connection refused",
        duration=0.1,
    )
    assert event.error == "connection refused"
