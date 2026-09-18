from typing import Any
from uuid import uuid4

import pytest
from packages.agent.llm.contract import LLMResponse, ToolCall
from packages.agent.llm.mock import MockLLMProvider
from packages.agent.runtime.events import (
    AgentCompletedEvent,
    ToolDeniedEvent,
    ToolExecutedEvent,
    ToolRequestedEvent,
)
from packages.agent.runtime.runtime import AgentRuntime
from packages.agent.runtime.state import AgentStatus
from packages.connectors.factory import create_connector, register_linux_tools
from packages.domain.models.agent import Agent
from packages.domain.models.organization import Organization
from packages.domain.models.policy import Policy as PolicyModel
from packages.domain.models.resource import Resource
from packages.mcp.client import MCPToolClient, MCPToolWrapper
from packages.mcp.server import NexusMCPServer
from packages.policies.evaluator import PolicyEvaluator
from packages.tools.registry import ToolRegistry

LINUX_TOOL_IDS = ["get_system_info", "get_cpu_usage", "get_memory_usage", "get_disk_usage"]


def _meminfo() -> str:
    return (
        "MemTotal: 8192000 kB\n"
        "MemFree: 2048000 kB\n"
        "MemAvailable: 6144000 kB\n"
        "SwapTotal: 2048000 kB\n"
        "SwapFree: 1536000 kB\n"
    )


def _df_output() -> str:
    return (
        "Filesystem      Size  Used Avail Use% Mounted on\n"
        "/dev/sda1        50G   25G   25G  50% /\n"
    )


def script_output(command: str) -> tuple[str, int]:
    """Deterministic fake SSH responses keyed on command substrings."""
    if command.startswith("hostname"):
        return "linux-lab-01", 0
    if command.startswith("uname -r"):
        return "5.15.0-91-generic", 0
    if "os-release" in command:
        return "Ubuntu 24.04 LTS", 0
    if command.startswith("uname -m"):
        return "x86_64", 0
    if command.startswith("uptime"):
        return "1 hour, 30 minutes", 0
    if "/proc/stat" in command or "awk" in command:
        return "42.5", 0
    if command.startswith("cat /proc/loadavg"):
        return "0.50 0.75 1.00 1/200 1234", 0
    if command.startswith("nproc"):
        return "4", 0
    if command.startswith("cat /proc/meminfo"):
        return _meminfo(), 0
    if command.startswith("df -h"):
        return _df_output(), 0
    return "", 0


class FakeSSHConnection:
    """A fake asyncssh transport that never leaves the process."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def close(self) -> None:
        pass

    async def wait_closed(self) -> None:
        pass

    async def run(self, command: str, timeout: float | None = None, **kwargs: Any) -> Any:
        self.calls.append(command)
        stdout, exit_status = script_output(command)
        from unittest.mock import MagicMock

        result = MagicMock()
        result.stdout = stdout
        result.stderr = "" if exit_status == 0 else "error"
        result.exit_status = exit_status
        return result


def make_resource() -> Resource:
    return Resource(
        organization_id=uuid4(),
        workspace_id=None,
        name="linux-lab-01",
        resource_type="linux_server",
    )


async def build_scenario(denied: list[str] | None = None, fake: FakeSSHConnection | None = None):
    fake = fake or FakeSSHConnection()
    resource = make_resource()
    connector = create_connector(resource)
    connector._connection = fake
    connector._connected = True

    server_registry = ToolRegistry()
    register_linux_tools(connector, server_registry)

    mcp_server = NexusMCPServer(name="nexus-linux", registry=server_registry)
    mcp_client = MCPToolClient(server_name="nexus-linux")
    await mcp_client.connect(mcp_server.server)

    discovered = await mcp_client.list_tools()
    runtime_registry = ToolRegistry()
    wrappers: list[MCPToolWrapper] = []
    for tool_def in discovered:
        wrapper = mcp_client.create_tool_wrapper(tool_def)
        runtime_registry.register(wrapper)
        wrappers.append(wrapper)

    org = Organization(name="LinuxLabOrg")
    agent = Agent(
        organization_id=org.id,
        workspace_id=uuid4(),
        name="Linux Investigator",
        role="investigator",
        autonomy_level="read_only",
        allowed_tool_ids=[],
    )

    policy = PolicyModel(
        organization_id=org.id,
        name="linux-policy",
        allowed_tool_ids=LINUX_TOOL_IDS,
        denied_tool_ids=denied or [],
    )
    evaluator = PolicyEvaluator(policy)

    return {
        "mcp_client": mcp_client,
        "connector": connector,
        "fake": fake,
        "resource": resource,
        "runtime_registry": runtime_registry,
        "wrappers": wrappers,
        "policy": evaluator,
        "agent": agent,
        "org": org,
    }


class TestLinuxAgentE2E:
    @pytest.mark.asyncio
    async def test_end_to_end_via_mcp_fake_ssh(self):
        scenario = await build_scenario()
        allowed = LINUX_TOOL_IDS

        llm = MockLLMProvider(
            [
                LLMResponse(
                    content="",
                    tool_calls=[ToolCall(id="1", tool_name="get_system_info", arguments={})],
                ),
                LLMResponse(
                    content="",
                    tool_calls=[ToolCall(id="2", tool_name="get_cpu_usage", arguments={})],
                ),
                LLMResponse(
                    content="",
                    tool_calls=[ToolCall(id="3", tool_name="get_memory_usage", arguments={})],
                ),
                LLMResponse(
                    content="",
                    tool_calls=[ToolCall(id="4", tool_name="get_disk_usage", arguments={})],
                ),
                LLMResponse(content="Linux server inspected; all systems nominal."),
            ]
        )
        runtime = AgentRuntime(
            llm=llm,
            registry=scenario["runtime_registry"],
            policy=scenario["policy"],
            max_iterations=10,
        )

        result = await runtime.run(
            "Inspect the current state of the Linux server.",
            scenario["agent"],
            allowed_tool_identifiers=allowed,
        )
        await scenario["mcp_client"].disconnect()

        assert result.status == AgentStatus.COMPLETED
        assert result.final_result == "Linux server inspected; all systems nominal."
        assert len(result.observations) == 4

        requested = runtime.events.get_by_type(ToolRequestedEvent)
        assert len(requested) == 4
        names = [e.tool_name for e in requested]
        assert names == ["get_system_info", "get_cpu_usage", "get_memory_usage", "get_disk_usage"]

        denied = runtime.events.get_by_type(ToolDeniedEvent)
        assert len(denied) == 0

        executed = runtime.events.get_by_type(ToolExecutedEvent)
        assert len(executed) == 4
        for e in executed:
            assert e.success is True
            assert e.duration > 0
            assert e.resource_mode == "real"
            assert e.resource_id is not None

        # MCP wrapping was used (runtime saw wrappers, not raw Linux tools)
        assert all(isinstance(w, MCPToolWrapper) for w in scenario["wrappers"])

        # The path reached the fake SSH transport with real command strings
        assert len(scenario["fake"].calls) >= 4

    @pytest.mark.asyncio
    async def test_observability_records_mode_real(self):
        scenario = await build_scenario()
        llm = MockLLMProvider(
            [
                LLMResponse(
                    content="",
                    tool_calls=[ToolCall(id="1", tool_name="get_system_info", arguments={})],
                ),
                LLMResponse(content="done"),
            ]
        )
        runtime = AgentRuntime(
            llm=llm,
            registry=scenario["runtime_registry"],
            policy=scenario["policy"],
            max_iterations=10,
        )
        await runtime.run(
            "Inspect server", scenario["agent"], allowed_tool_identifiers=LINUX_TOOL_IDS
        )
        await scenario["mcp_client"].disconnect()

        executed = runtime.events.get_by_type(ToolExecutedEvent)
        assert len(executed) == 1
        e = executed[0]
        assert e.tool_name == "get_system_info"
        assert e.success is True
        assert e.resource_mode == "real"
        assert e.resource_id is not None
        assert isinstance(e.duration, float)

        completed = runtime.events.get_by_type(AgentCompletedEvent)
        assert len(completed) == 1

    @pytest.mark.asyncio
    async def test_denied_linux_tool_blocked_before_connector(self):
        scenario = await build_scenario(denied=["get_disk_usage"])
        llm = MockLLMProvider(
            [
                LLMResponse(
                    content="",
                    tool_calls=[ToolCall(id="1", tool_name="get_disk_usage", arguments={})],
                ),
                LLMResponse(content="skipped"),
            ]
        )
        runtime = AgentRuntime(
            llm=llm,
            registry=scenario["runtime_registry"],
            policy=scenario["policy"],
            max_iterations=10,
        )
        await runtime.run(
            "Inspect disk", scenario["agent"], allowed_tool_identifiers=LINUX_TOOL_IDS
        )
        await scenario["mcp_client"].disconnect()

        denied = runtime.events.get_by_type(ToolDeniedEvent)
        assert len(denied) == 1
        assert denied[0].tool_name == "get_disk_usage"
        assert "denied" in denied[0].reason.lower()

        executed = runtime.events.get_by_type(ToolExecutedEvent)
        assert len(executed) == 0
        # The denied tool never reached the SSH transport
        assert scenario["fake"].calls == []

    @pytest.mark.asyncio
    async def test_unknown_tool_rejected_before_mcp_execution(self):
        scenario = await build_scenario()
        llm = MockLLMProvider(
            [
                LLMResponse(
                    content="",
                    tool_calls=[ToolCall(id="1", tool_name="nonexistent_tool", arguments={})],
                ),
                LLMResponse(content="done"),
            ]
        )
        runtime = AgentRuntime(
            llm=llm,
            registry=scenario["runtime_registry"],
            policy=scenario["policy"],
            max_iterations=10,
        )
        await runtime.run("Inspect", scenario["agent"], allowed_tool_identifiers=LINUX_TOOL_IDS)
        await scenario["mcp_client"].disconnect()

        denied = runtime.events.get_by_type(ToolDeniedEvent)
        assert len(denied) == 1
        assert denied[0].tool_name == "nonexistent_tool"
        assert "unknown" in denied[0].reason.lower()

        executed = runtime.events.get_by_type(ToolExecutedEvent)
        assert len(executed) == 0
        assert scenario["fake"].calls == []

    @pytest.mark.asyncio
    async def test_linux_tools_are_read_only_and_real_mode(self):
        scenario = await build_scenario()
        wrapper_ids = {w.get_identifier() for w in scenario["wrappers"]}
        assert set(LINUX_TOOL_IDS).issubset(wrapper_ids)
        for w in scenario["wrappers"]:
            assert w.is_read_only() is True
            assert w.get_resource_mode() == "real"
            assert w.get_resource_id() is not None
            assert w.get_risk_level().value == "low"
        await scenario["mcp_client"].disconnect()
