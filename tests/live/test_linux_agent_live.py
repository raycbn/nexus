from uuid import uuid4

import pytest
from packages.agent.llm.contract import LLMResponse, ToolCall
from packages.agent.llm.mock import MockLLMProvider
from packages.agent.runtime.events import ToolExecutedEvent
from packages.agent.runtime.runtime import AgentRuntime
from packages.agent.runtime.state import AgentStatus
from packages.connectors.factory import create_connector, register_linux_tools
from packages.domain.models.agent import Agent
from packages.domain.models.organization import Organization
from packages.domain.models.policy import Policy as PolicyModel
from packages.domain.models.resource import Resource
from packages.mcp.client import MCPToolClient
from packages.mcp.server import NexusMCPServer
from packages.policies.evaluator import PolicyEvaluator
from packages.tools.registry import ToolRegistry

LINUX_TOOL_IDS = ["get_system_info", "get_cpu_usage", "get_memory_usage", "get_disk_usage"]


def _linux_resource() -> Resource:
    return Resource(
        organization_id=uuid4(),
        workspace_id=None,
        name="linux-lab-01",
        resource_type="linux_server",
    )


def _ollama_available() -> bool:
    try:
        import urllib.request

        urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=3)
        return True
    except Exception:
        return False


@pytest.mark.live
class TestLinuxAgentLive:
    @pytest.mark.asyncio
    async def test_runtime_executes_linux_tools_over_real_ssh(self):
        resource = _linux_resource()
        connector = create_connector(resource)
        await connector.connect(resource)
        assert connector.is_connected

        server_registry = ToolRegistry()
        register_linux_tools(connector, server_registry)

        mcp_server = NexusMCPServer(name="nexus-linux-live", registry=server_registry)
        mcp_client = MCPToolClient(server_name="nexus-linux-live")
        await mcp_client.connect(mcp_server.server)

        discovered = await mcp_client.list_tools()
        runtime_registry = ToolRegistry()
        for tool_def in discovered:
            runtime_registry.register(mcp_client.create_tool_wrapper(tool_def))

        org = Organization(name="LinuxLabOrg")
        agent = Agent(
            organization_id=org.id,
            workspace_id=uuid4(),
            name="Linux Live Agent",
            role="investigator",
            autonomy_level="read_only",
            allowed_tool_ids=[],
        )
        policy = PolicyModel(
            organization_id=org.id,
            name="linux-live-policy",
            allowed_tool_ids=LINUX_TOOL_IDS,
        )
        evaluator = PolicyEvaluator(policy)

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
                LLMResponse(content="Inspected linux-lab-01 via SSH."),
            ]
        )

        runtime = AgentRuntime(
            llm=llm,
            registry=runtime_registry,
            policy=evaluator,
            max_iterations=10,
        )

        result = await runtime.run(
            "Inspect the current state of the Linux server.",
            agent,
            allowed_tool_identifiers=LINUX_TOOL_IDS,
        )

        await mcp_client.disconnect()
        await connector.disconnect(resource)

        assert result.status == AgentStatus.COMPLETED
        assert result.final_result == "Inspected linux-lab-01 via SSH."

        executed = runtime.events.get_by_type(ToolExecutedEvent)
        assert len(executed) == 4
        for e in executed:
            assert e.success is True
            assert e.resource_mode == "real"
            assert e.resource_id is not None

    @pytest.mark.asyncio
    @pytest.mark.skipif(not _ollama_available(), reason="Ollama not reachable")
    async def test_linux_agent_ollama_e2e(self):
        from packages.agent.llm.ollama import OllamaProvider

        resource = _linux_resource()
        connector = create_connector(resource)
        await connector.connect(resource)
        assert connector.is_connected

        server_registry = ToolRegistry()
        register_linux_tools(connector, server_registry)

        mcp_server = NexusMCPServer(name="nexus-linux-ollama", registry=server_registry)
        mcp_client = MCPToolClient(server_name="nexus-linux-ollama")
        await mcp_client.connect(mcp_server.server)

        discovered = await mcp_client.list_tools()
        runtime_registry = ToolRegistry()
        for tool_def in discovered:
            runtime_registry.register(mcp_client.create_tool_wrapper(tool_def))

        org = Organization(name="LinuxLabOrg")
        agent = Agent(
            organization_id=org.id,
            workspace_id=uuid4(),
            name="Linux Ollama Agent",
            role="investigator",
            autonomy_level="read_only",
            allowed_tool_ids=[],
        )
        policy = PolicyModel(
            organization_id=org.id,
            name="linux-ollama-policy",
            allowed_tool_ids=LINUX_TOOL_IDS,
        )
        evaluator = PolicyEvaluator(policy)

        llm = OllamaProvider(registry=runtime_registry)
        runtime = AgentRuntime(
            llm=llm,
            registry=runtime_registry,
            policy=evaluator,
            max_iterations=6,
        )

        result = await runtime.run(
            "Inspect the current state of the Linux server. "
            "Report hostname, CPU, memory and disk usage.",
            agent,
            allowed_tool_identifiers=LINUX_TOOL_IDS,
        )

        await mcp_client.disconnect()
        await connector.disconnect(resource)

        assert result.status != AgentStatus.FAILED
        executed = runtime.events.get_by_type(ToolExecutedEvent)
        for e in executed:
            assert e.resource_mode == "real"
