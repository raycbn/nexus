import pytest
from packages.connectors.providers.linux import LinuxConnector
from packages.domain.models.resource import Resource
from packages.tools.base import Tool
from packages.tools.providers.linux_tools import (
    GetCpuUsageTool,
    GetDiskUsageTool,
    GetMemoryUsageTool,
    GetNetworkListenersTool,
    GetProcessesTool,
    GetServiceStatusTool,
    GetSystemInfoTool,
)


@pytest.fixture
def resource():
    return Resource(
        organization_id="00000000-0000-0000-0000-000000000001",
        workspace_id=None,
        name="linux-lab-01",
        resource_type="linux_server",
    )


@pytest.fixture
def connector(resource):
    return LinuxConnector(
        resource=resource,
        host="localhost",
        username="test",
        auth_ref="/fake/key",
    )


@pytest.fixture
def mock_connector(resource):
    from unittest.mock import AsyncMock, MagicMock

    conn = LinuxConnector(
        resource=resource,
        host="localhost",
        username="test",
        auth_ref="/fake/key",
    )
    mock_ssh = MagicMock()
    mock_ssh.close = MagicMock()
    mock_ssh.wait_closed = MagicMock()

    async def mock_run(command, timeout=None, **kwargs):
        result = MagicMock()
        result.stdout = ""
        result.stderr = ""
        result.exit_status = 0
        return result

    mock_ssh.run = AsyncMock(side_effect=mock_run)
    conn._connection = mock_ssh
    conn._connected = True
    return conn


class TestLinuxToolsInterface:
    @pytest.mark.asyncio
    async def test_get_system_info_tool_is_tool(self, mock_connector):
        tool = GetSystemInfoTool(mock_connector)
        assert isinstance(tool, Tool)

    @pytest.mark.asyncio
    async def test_all_tools_are_read_only(self, mock_connector):
        tools = [
            GetSystemInfoTool(mock_connector),
            GetCpuUsageTool(mock_connector),
            GetMemoryUsageTool(mock_connector),
            GetDiskUsageTool(mock_connector),
            GetProcessesTool(mock_connector),
            GetNetworkListenersTool(mock_connector),
            GetServiceStatusTool(mock_connector),
        ]
        for tool in tools:
            assert tool.is_read_only() is True
            assert tool.get_resource_mode() == "real"
            assert tool.get_required_permissions() == ["read"]

    @pytest.mark.asyncio
    async def test_all_tools_have_stable_identifiers(self, mock_connector):
        assert GetSystemInfoTool(mock_connector).get_identifier() == "get_system_info"
        assert GetCpuUsageTool(mock_connector).get_identifier() == "get_cpu_usage"
        assert GetMemoryUsageTool(mock_connector).get_identifier() == "get_memory_usage"
        assert GetDiskUsageTool(mock_connector).get_identifier() == "get_disk_usage"
        assert GetProcessesTool(mock_connector).get_identifier() == "get_processes"
        assert GetNetworkListenersTool(mock_connector).get_identifier() == "get_network_listeners"
        assert GetServiceStatusTool(mock_connector).get_identifier() == "get_service_status"

    @pytest.mark.asyncio
    async def test_all_tools_have_low_risk(self, mock_connector):
        from packages.domain.models.enums import RiskLevel

        tools = [
            GetSystemInfoTool(mock_connector),
            GetCpuUsageTool(mock_connector),
            GetMemoryUsageTool(mock_connector),
            GetDiskUsageTool(mock_connector),
            GetProcessesTool(mock_connector),
            GetNetworkListenersTool(mock_connector),
            GetServiceStatusTool(mock_connector),
        ]
        for tool in tools:
            assert tool.get_risk_level() == RiskLevel.LOW


class TestGetSystemInfoTool:
    @pytest.mark.asyncio
    async def test_execute_returns_structured_data(self, mock_connector):
        from unittest.mock import AsyncMock, MagicMock

        responses = {
            "hostname -s": "linux-lab-01",
            "uname -r": "5.15.0-generic",
            "cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2 | tr -d '\"'": "Ubuntu 24.04 LTS",
            "uname -m": "x86_64",
            "uptime -p | sed 's/up //'": "2 hours, 30 minutes",
        }

        async def mock_run(command, timeout=None, **kwargs):
            result = MagicMock()
            result.stdout = responses.get(command, "")
            result.stderr = ""
            result.exit_status = 0
            return result

        mock_connector._connection.run = AsyncMock(side_effect=mock_run)
        tool = GetSystemInfoTool(mock_connector)
        result = await tool.execute({})
        assert result["hostname"] == "linux-lab-01"
        assert result["mode"] == "real"
        assert "kernel" in result
        assert "os" in result


class TestGetCpuUsageTool:
    @pytest.mark.asyncio
    async def test_execute_returns_cpu_data(self, mock_connector):
        from unittest.mock import AsyncMock, MagicMock

        responses = {
            "grep 'cpu ' /proc/stat | awk "
            "'{usage=100-($5*100)/($2+$3+$4+$5+$6+$7+$8)}; END{printf \"%.1f\", usage}'": "42.5",
            "cat /proc/loadavg": "0.50 0.75 1.00 1/200 1234",
            "nproc": "4",
        }

        async def mock_run(command, timeout=None, **kwargs):
            result = MagicMock()
            result.stdout = responses.get(command, "")
            result.stderr = ""
            result.exit_status = 0
            return result

        mock_connector._connection.run = AsyncMock(side_effect=mock_run)
        tool = GetCpuUsageTool(mock_connector)
        result = await tool.execute({})
        assert result["mode"] == "real"
        assert isinstance(result["cpu_percent"], float)
        assert isinstance(result["cpu_count"], int)


class TestGetMemoryUsageTool:
    @pytest.mark.asyncio
    async def test_execute_returns_memory_data(self, mock_connector):
        from unittest.mock import AsyncMock, MagicMock

        meminfo = """MemTotal: 8192000 kB
MemAvailable: 6144000 kB
SwapTotal: 2048000 kB
SwapFree: 2048000 kB"""

        async def mock_run(command, timeout=None, **kwargs):
            result = MagicMock()
            if "cat /proc/meminfo" in command:
                result.stdout = meminfo
            else:
                result.stdout = ""
            result.stderr = ""
            result.exit_status = 0
            return result

        mock_connector._connection.run = AsyncMock(side_effect=mock_run)
        tool = GetMemoryUsageTool(mock_connector)
        result = await tool.execute({})
        assert result["mode"] == "real"
        assert result["total_mb"] > 0
        assert result["used_mb"] >= 0
        assert result["available_mb"] > 0


class TestGetDiskUsageTool:
    @pytest.mark.asyncio
    async def test_execute_returns_disk_data(self, mock_connector):
        from unittest.mock import AsyncMock, MagicMock

        df_output = """Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1        50G   25G   25G  50% /
tmpfs            64M     0   64M   0% /dev"""

        async def mock_run(command, timeout=None, **kwargs):
            result = MagicMock()
            if "df -h" in command:
                result.stdout = df_output
            else:
                result.stdout = ""
            result.stderr = ""
            result.exit_status = 0
            return result

        mock_connector._connection.run = AsyncMock(side_effect=mock_run)
        tool = GetDiskUsageTool(mock_connector)
        result = await tool.execute({})
        assert result["mode"] == "real"
        assert isinstance(result["disks"], list)
        if result["disks"]:
            assert "filesystem" in result["disks"][0]


class TestGetProcessesTool:
    @pytest.mark.asyncio
    async def test_execute_returns_processes(self, mock_connector):
        from unittest.mock import AsyncMock, MagicMock

        ps_output = """   1 systemd    0.0  0.1
   2 sshd     0.5  0.2
 100 nginx    1.2  0.5"""

        async def mock_run(command, timeout=None, **kwargs):
            result = MagicMock()
            if "ps -eo" in command:
                result.stdout = ps_output
            else:
                result.stdout = ""
            result.stderr = ""
            result.exit_status = 0
            return result

        mock_connector._connection.run = AsyncMock(side_effect=mock_run)
        tool = GetProcessesTool(mock_connector)
        result = await tool.execute({})
        assert result["mode"] == "real"
        assert isinstance(result["processes"], list)
        if result["processes"]:
            assert "pid" in result["processes"][0]
            assert "name" in result["processes"][0]


class TestGetNetworkListenersTool:
    @pytest.mark.asyncio
    async def test_execute_returns_listeners(self, mock_connector):
        from unittest.mock import AsyncMock, MagicMock

        ss_output = """State  Recv-Q  Send-Q  Local Address:Port  Peer Address:Port  Process
LISTEN 0       128     0.0.0.0:22         0.0.0.0:*          users:(("sshd",pid=1,fd=3))
LISTEN 0       128     0.0.0.0:80         0.0.0.0:*          users:(("nginx",pid=2,fd=6))"""

        async def mock_run(command, timeout=None, **kwargs):
            result = MagicMock()
            if "ss -tlnp" in command:
                result.stdout = ss_output
            else:
                result.stdout = ""
            result.stderr = ""
            result.exit_status = 0
            return result

        mock_connector._connection.run = AsyncMock(side_effect=mock_run)
        tool = GetNetworkListenersTool(mock_connector)
        result = await tool.execute({})
        assert result["mode"] == "real"
        assert isinstance(result["listeners"], list)
        if result["listeners"]:
            assert "protocol" in result["listeners"][0]
            assert "port" in result["listeners"][0]


class TestGetServiceStatusTool:
    @pytest.mark.asyncio
    async def test_execute_returns_service_status(self, mock_connector):
        from unittest.mock import AsyncMock, MagicMock

        async def mock_run(command, timeout=None, **kwargs):
            result = MagicMock()
            if "sshd" in command:
                result.stdout = "1"
            elif "nginx" in command or "python3" in command:
                result.stdout = ""
            else:
                result.stdout = ""
            result.stderr = ""
            result.exit_status = 0 if command != "bad" else 1
            return result

        mock_connector._connection.run = AsyncMock(side_effect=mock_run)
        tool = GetServiceStatusTool(mock_connector)
        result = await tool.execute({})
        assert result["mode"] == "real"
        assert "sshd" in result
        assert "nginx" in result
        assert "python_api" in result


class TestLinuxToolsResourceMode:
    @pytest.mark.asyncio
    async def test_tools_are_real_mode(self, mock_connector):
        tools = [
            GetSystemInfoTool(mock_connector),
            GetCpuUsageTool(mock_connector),
            GetMemoryUsageTool(mock_connector),
            GetDiskUsageTool(mock_connector),
            GetProcessesTool(mock_connector),
            GetNetworkListenersTool(mock_connector),
            GetServiceStatusTool(mock_connector),
        ]
        for tool in tools:
            assert tool.get_resource_mode() == "real"


class TestLinuxToolsSchemas:
    @pytest.mark.asyncio
    async def test_tools_have_schemas(self, mock_connector):
        tools = [
            GetSystemInfoTool(mock_connector),
            GetCpuUsageTool(mock_connector),
            GetMemoryUsageTool(mock_connector),
            GetDiskUsageTool(mock_connector),
            GetProcessesTool(mock_connector),
            GetNetworkListenersTool(mock_connector),
            GetServiceStatusTool(mock_connector),
        ]
        for tool in tools:
            assert isinstance(tool.get_input_schema(), dict)
            assert isinstance(tool.get_output_schema(), dict)


class TestLinuxToolsNoArbitraryExecution:
    @pytest.mark.asyncio
    async def test_tools_do_not_accept_arbitrary_commands(self, mock_connector):
        tool = GetSystemInfoTool(mock_connector)
        result = await tool.execute({})
        assert result is not None
        assert "hostname" in result

    @pytest.mark.asyncio
    async def test_tools_ignore_arbitrary_parameters(self, mock_connector):
        tools = [
            GetSystemInfoTool(mock_connector),
            GetCpuUsageTool(mock_connector),
            GetMemoryUsageTool(mock_connector),
            GetDiskUsageTool(mock_connector),
            GetProcessesTool(mock_connector),
            GetNetworkListenersTool(mock_connector),
            GetServiceStatusTool(mock_connector),
        ]
        for tool in tools:
            assert "command" not in tool.get_input_schema().get("properties", {})
