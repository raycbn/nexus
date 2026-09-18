import os

import pytest
from packages.connectors.providers.linux import LinuxConnector
from packages.domain.models.resource import Resource
from packages.tools.providers.linux_tools import (
    GetCpuUsageTool,
    GetDiskUsageTool,
    GetMemoryUsageTool,
    GetNetworkListenersTool,
    GetProcessesTool,
    GetServiceStatusTool,
    GetSystemInfoTool,
)

LAB_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "infrastructure", "lab")
SSH_KEY = os.path.join(LAB_DIR, "ssh_key")


@pytest.fixture
def linux_resource():
    return Resource(
        organization_id="00000000-0000-0000-0000-000000000001",
        workspace_id=None,
        name="linux-lab-01",
        resource_type="linux_server",
    )


@pytest.fixture
def linux_connector(linux_resource):
    connector = LinuxConnector(
        resource=linux_resource,
        host="localhost",
        port=2222,
        username="nexus",
        auth_ref=SSH_KEY,
        connect_timeout=10.0,
        command_timeout=30.0,
    )
    return connector


@pytest.mark.live
class TestLinuxConnectorLive:
    @pytest.mark.asyncio
    async def test_ssh_connection(self, linux_connector, linux_resource):
        await linux_connector.connect(linux_resource)
        assert linux_connector.is_connected is True
        await linux_connector.disconnect(linux_resource)
        assert linux_connector.is_connected is False

    @pytest.mark.asyncio
    async def test_health_check(self, linux_connector, linux_resource):
        await linux_connector.connect(linux_resource)
        status = await linux_connector.health_check(linux_resource)
        assert status.healthy is True
        await linux_connector.disconnect(linux_resource)

    @pytest.mark.asyncio
    async def test_get_system_info(self, linux_connector, linux_resource):
        await linux_connector.connect(linux_resource)
        tool = GetSystemInfoTool(linux_connector)
        result = await tool.execute({})
        assert result["mode"] == "real"
        assert result["hostname"]
        assert result["kernel"]
        assert result["architecture"]
        await linux_connector.disconnect(linux_resource)

    @pytest.mark.asyncio
    async def test_get_cpu_usage(self, linux_connector, linux_resource):
        await linux_connector.connect(linux_resource)
        tool = GetCpuUsageTool(linux_connector)
        result = await tool.execute({})
        assert result["mode"] == "real"
        assert isinstance(result["cpu_percent"], (int, float))
        assert result["cpu_count"] > 0
        await linux_connector.disconnect(linux_resource)

    @pytest.mark.asyncio
    async def test_get_memory_usage(self, linux_connector, linux_resource):
        await linux_connector.connect(linux_resource)
        tool = GetMemoryUsageTool(linux_connector)
        result = await tool.execute({})
        assert result["mode"] == "real"
        assert result["total_mb"] > 0
        assert result["used_mb"] >= 0
        assert result["available_mb"] > 0
        await linux_connector.disconnect(linux_resource)

    @pytest.mark.asyncio
    async def test_get_disk_usage(self, linux_connector, linux_resource):
        await linux_connector.connect(linux_resource)
        tool = GetDiskUsageTool(linux_connector)
        result = await tool.execute({})
        assert result["mode"] == "real"
        assert isinstance(result["disks"], list)
        await linux_connector.disconnect(linux_resource)

    @pytest.mark.asyncio
    async def test_get_processes(self, linux_connector, linux_resource):
        await linux_connector.connect(linux_resource)
        tool = GetProcessesTool(linux_connector)
        result = await tool.execute({})
        assert result["mode"] == "real"
        assert isinstance(result["processes"], list)
        await linux_connector.disconnect(linux_resource)

    @pytest.mark.asyncio
    async def test_get_network_listeners(self, linux_connector, linux_resource):
        await linux_connector.connect(linux_resource)
        tool = GetNetworkListenersTool(linux_connector)
        result = await tool.execute({})
        assert result["mode"] == "real"
        assert isinstance(result["listeners"], list)
        await linux_connector.disconnect(linux_resource)

    @pytest.mark.asyncio
    async def test_get_service_status(self, linux_connector, linux_resource):
        await linux_connector.connect(linux_resource)
        tool = GetServiceStatusTool(linux_connector)
        result = await tool.execute({})
        assert result["mode"] == "real"
        assert "sshd" in result
        assert "nginx" in result
        assert "python_api" in result
        await linux_connector.disconnect(linux_resource)


@pytest.mark.live
class TestLinuxToolsLive:
    @pytest.mark.asyncio
    async def test_all_tools_execute(self, linux_connector, linux_resource):
        await linux_connector.connect(linux_resource)
        tools = [
            GetSystemInfoTool(linux_connector),
            GetCpuUsageTool(linux_connector),
            GetMemoryUsageTool(linux_connector),
            GetDiskUsageTool(linux_connector),
            GetProcessesTool(linux_connector),
            GetNetworkListenersTool(linux_connector),
            GetServiceStatusTool(linux_connector),
        ]
        for tool in tools:
            result = await tool.execute({})
            assert result is not None
            assert "resource_id" in result
            assert result["mode"] == "real"
        await linux_connector.disconnect(linux_resource)


@pytest.mark.live
class TestLinuxConnectorLiveTypedErrors:
    @pytest.mark.asyncio
    async def test_disconnect_then_health_check(self, linux_connector, linux_resource):
        status = await linux_connector.health_check(linux_resource)
        assert status.healthy is False

    @pytest.mark.asyncio
    async def test_disconnect_then_execute_read(self, linux_connector, linux_resource):
        from packages.domain.exceptions import ConnectorUnavailableError

        with pytest.raises(ConnectorUnavailableError):
            await linux_connector.execute_read(linux_resource, "echo test")
