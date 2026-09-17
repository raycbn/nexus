import pytest
from packages.tools.providers.mock_tools import GetCpuUsageTool, GetSystemInfoTool
from packages.tools.registry import ToolRegistry


def test_register_tool():
    registry = ToolRegistry()
    tool = GetSystemInfoTool()
    registry.register(tool)
    assert registry.has("get_system_info")
    assert registry.count() == 1


def test_register_multiple_tools():
    registry = ToolRegistry()
    registry.register(GetSystemInfoTool())
    registry.register(GetCpuUsageTool())
    assert registry.count() == 2
    assert registry.has("get_system_info")
    assert registry.has("get_cpu_usage")


def test_get_tool_by_identifier():
    registry = ToolRegistry()
    tool = GetSystemInfoTool()
    registry.register(tool)
    retrieved = registry.get("get_system_info")
    assert retrieved is not None
    assert retrieved.get_identifier() == "get_system_info"


def test_get_missing_tool_returns_none():
    registry = ToolRegistry()
    registry.register(GetSystemInfoTool())
    assert registry.get("nonexistent") is None


def test_duplicate_registration_raises():
    registry = ToolRegistry()
    registry.register(GetSystemInfoTool())
    with pytest.raises(ValueError):
        registry.register(GetSystemInfoTool())


def test_list_tools():
    registry = ToolRegistry()
    tools = [GetSystemInfoTool(), GetCpuUsageTool()]
    for t in tools:
        registry.register(t)
    listed = registry.list_tools()
    assert len(listed) == 2
    identifiers = {t.get_identifier() for t in listed}
    assert "get_system_info" in identifiers
    assert "get_cpu_usage" in identifiers


def test_prevents_duplicate_identifiers():
    registry = ToolRegistry()
    registry.register(GetSystemInfoTool())
    with pytest.raises(ValueError) as exc_info:
        registry.register(GetSystemInfoTool())
    assert "already registered" in str(exc_info.value)


def test_empty_registry():
    registry = ToolRegistry()
    assert registry.count() == 0
    assert registry.list_tools() == []
    assert not registry.has("anything")
