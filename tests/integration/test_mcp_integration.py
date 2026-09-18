from uuid import uuid4

from packages.agent.llm.contract import LLMResponse, ToolCall
from packages.agent.llm.mock import MockLLMProvider
from packages.agent.runtime.events import (
    LLMResponseReceivedEvent,
    ObservationRecordedEvent,
    ToolAllowedEvent,
    ToolDeniedEvent,
    ToolExecutedEvent,
    ToolRequestedEvent,
)
from packages.agent.runtime.runtime import AgentRuntime
from packages.agent.runtime.state import AgentStatus
from packages.domain.models.agent import Agent
from packages.domain.models.organization import Organization
from packages.domain.models.policy import Policy as PolicyModel
from packages.mcp.client import MCPToolClient
from packages.mcp.server import NexusMCPServer
from packages.policies.evaluator import PolicyEvaluator
from packages.tools.providers.mock_tools import GetSystemInfoTool
from packages.tools.registry import ToolRegistry


async def test_mcp_integration_full_flow():
    server_registry = ToolRegistry()
    server_registry.register(GetSystemInfoTool())
    runtime_registry = ToolRegistry()

    mcp_server = NexusMCPServer(name="test", version="1.0", registry=server_registry)
    mcp_client = MCPToolClient(server_name="test")

    await mcp_client.connect(mcp_server.server)

    discovered = await mcp_client.list_tools()
    for tool_def in discovered:
        wrapper = mcp_client.create_tool_wrapper(tool_def)
        runtime_registry.register(wrapper)

    org = Organization(name="Test")
    agent = Agent(
        organization_id=org.id,
        workspace_id=uuid4(),
        name="Test Agent",
        role="investigator",
        autonomy_level="read_only",
        allowed_tool_ids=[],
    )

    policy = PolicyModel(
        organization_id=org.id,
        name="test-policy",
        allowed_tool_ids=["get_system_info"],
    )
    evaluator = PolicyEvaluator(policy)

    llm_responses = [
        LLMResponse(
            content="",
            tool_calls=[
                ToolCall(
                    id="1",
                    tool_name="get_system_info",
                    arguments={"target": "test-server"},
                )
            ],
        ),
        LLMResponse(content="System is healthy."),
    ]

    llm = MockLLMProvider(llm_responses)
    runtime = AgentRuntime(
        llm=llm,
        registry=runtime_registry,
        policy=evaluator,
        max_iterations=10,
    )

    result = await runtime.run(
        "Check the system",
        agent,
        allowed_tool_identifiers=["get_system_info"],
    )

    await mcp_client.disconnect()

    assert result.status == AgentStatus.COMPLETED
    assert result.final_result == "System is healthy."

    requested = runtime.events.get_by_type(ToolRequestedEvent)
    assert len(requested) == 1
    assert requested[0].tool_name == "get_system_info"

    allowed = runtime.events.get_by_type(ToolAllowedEvent)
    assert len(allowed) == 1

    executed = runtime.events.get_by_type(ToolExecutedEvent)
    assert len(executed) == 1
    assert executed[0].success is True

    observed = runtime.events.get_by_type(ObservationRecordedEvent)
    assert len(observed) == 1

    llm_events = runtime.events.get_by_type(LLMResponseReceivedEvent)
    assert len(llm_events) == 2


async def test_mcp_policy_denies_before_execution():
    server_registry = ToolRegistry()
    server_registry.register(GetSystemInfoTool())
    runtime_registry = ToolRegistry()

    mcp_server = NexusMCPServer(name="test", version="1.0", registry=server_registry)
    mcp_client = MCPToolClient(server_name="test")

    await mcp_client.connect(mcp_server.server)
    discovered = await mcp_client.list_tools()
    for tool_def in discovered:
        wrapper = mcp_client.create_tool_wrapper(tool_def)
        runtime_registry.register(wrapper)

    org = Organization(name="Test")
    agent = Agent(
        organization_id=org.id,
        workspace_id=uuid4(),
        name="Test Agent",
        role="investigator",
        autonomy_level="read_only",
        allowed_tool_ids=[],
    )

    policy = PolicyModel(
        organization_id=org.id,
        name="denied-policy",
        allowed_tool_ids=[],
        denied_tool_ids=["get_system_info"],
    )
    evaluator = PolicyEvaluator(policy)

    llm_responses = [
        LLMResponse(
            content="",
            tool_calls=[
                ToolCall(
                    id="1",
                    tool_name="get_system_info",
                    arguments={},
                )
            ],
        ),
        LLMResponse(content="Done"),
    ]

    llm = MockLLMProvider(llm_responses)
    runtime = AgentRuntime(
        llm=llm,
        registry=runtime_registry,
        policy=evaluator,
        max_iterations=10,
    )

    await runtime.run("Check system", agent, allowed_tool_identifiers=["get_system_info"])

    await mcp_client.disconnect()

    denied = runtime.events.get_by_type(ToolDeniedEvent)
    assert len(denied) == 1
    assert denied[0].tool_name == "get_system_info"

    executed = runtime.events.get_by_type(ToolExecutedEvent)
    assert len(executed) == 0
