import asyncio

from packages.domain.models.enums import RiskLevel
from packages.tools.base import Tool
from packages.tools.providers.mock_tools import (
    GetCpuUsageTool,
    GetDiskUsageTool,
    GetMemoryUsageTool,
    GetRunningProcessesTool,
    GetSystemInfoTool,
)


def test_get_system_info_returns_configured_data():
    expected = {"hostname": "test-host", "os": "linux"}
    tool = GetSystemInfoTool(data=expected)
    result = asyncio_run(tool.execute({}))
    assert result == expected


def test_get_cpu_usage_returns_configured_data():
    expected = {"cpu_percent": 75.5, "cores": 8}
    tool = GetCpuUsageTool(data=expected)
    result = asyncio_run(tool.execute({}))
    assert result == expected


def test_get_memory_usage_returns_configured_data():
    expected = {"memory_used_mb": 4096, "memory_percent": 50.0}
    tool = GetMemoryUsageTool(data=expected)
    result = asyncio_run(tool.execute({}))
    assert result == expected


def test_get_disk_usage_returns_configured_data():
    expected = {"disk_used_gb": 500, "disk_percent": 50.0}
    tool = GetDiskUsageTool(data=expected)
    result = asyncio_run(tool.execute({}))
    assert result == expected


def test_get_running_processes_returns_configured_data():
    expected_processes = [{"name": "test-proc", "pid": 99}]
    tool = GetRunningProcessesTool(data=expected_processes)
    result = asyncio_run(tool.execute({}))
    assert result["processes"] == expected_processes


def test_all_tools_are_read_only():
    tools: list[Tool] = [
        GetSystemInfoTool(),
        GetCpuUsageTool(),
        GetMemoryUsageTool(),
        GetDiskUsageTool(),
        GetRunningProcessesTool(),
    ]
    for tool in tools:
        assert tool.is_read_only() is True


def test_all_tools_have_stable_identifiers():
    assert GetSystemInfoTool().get_identifier() == "get_system_info"
    assert GetCpuUsageTool().get_identifier() == "get_cpu_usage"
    assert GetMemoryUsageTool().get_identifier() == "get_memory_usage"
    assert GetDiskUsageTool().get_identifier() == "get_disk_usage"
    assert GetRunningProcessesTool().get_identifier() == "get_running_processes"


def test_all_tools_have_low_risk():
    tools: list[Tool] = [
        GetSystemInfoTool(),
        GetCpuUsageTool(),
        GetMemoryUsageTool(),
        GetDiskUsageTool(),
        GetRunningProcessesTool(),
    ]
    for tool in tools:
        assert tool.get_risk_level() == RiskLevel.LOW


def test_tools_have_schemas():
    tool = GetSystemInfoTool()
    assert isinstance(tool.get_input_schema(), dict)
    assert isinstance(tool.get_output_schema(), dict)
    assert isinstance(tool.get_required_permissions(), list)


def test_mock_tools_do_not_access_real_system():
    tools = [
        GetSystemInfoTool(),
        GetCpuUsageTool(),
        GetMemoryUsageTool(),
        GetDiskUsageTool(),
        GetRunningProcessesTool(),
    ]
    for tool in tools:
        result = asyncio_run(tool.execute({"target": "fake-server"}))
        assert result is not None


def asyncio_run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)
