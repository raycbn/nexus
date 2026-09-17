import asyncio
from uuid import uuid4

from packages.agent.llm.contract import LLMResponse
from packages.agent.llm.mock import MockLLMProvider
from packages.agent.runtime.events import (
    AgentCompletedEvent,
    AgentStartedEvent,
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
from packages.policies.evaluator import PolicyEvaluator
from packages.tools.providers.mock_tools import (
    GetSystemInfoTool,
)
from packages.tools.registry import ToolRegistry


def make_agent():
    org = Organization(name="Test")
    return Agent(
        organization_id=org.id,
        workspace_id=uuid4(),
        name="Test Agent",
        role="investigator",
        autonomy_level="read_only",
        allowed_tool_ids=[],
    )


def test_full_observation_flow():
    llm_responses = [
        LLMResponse(
            content="",
            tool_calls=[{"id": "1", "tool_name": "get_system_info", "arguments": {}}],
        ),
        LLMResponse(content="Investigation complete"),
    ]

    tool = GetSystemInfoTool(data={"hostname": "test"})
    registry = ToolRegistry()
    registry.register(tool)

    policy = PolicyModel(
        organization_id=uuid4(),
        name="test",
        allowed_tool_ids=["get_system_info"],
    )

    llm = MockLLMProvider(llm_responses)
    evaluator = PolicyEvaluator(policy)
    runtime = AgentRuntime(llm=llm, registry=registry, policy=evaluator, max_iterations=10)
    agent = make_agent()

    result = asyncio_run(
        runtime.run("Check server", agent, allowed_tool_identifiers=["get_system_info"])
    )

    assert result.status == AgentStatus.COMPLETED
    assert result.final_result == "Investigation complete"
    assert len(result.observations) == 1

    started = runtime.events.get_by_type(AgentStartedEvent)
    assert len(started) == 1

    llm_events = runtime.events.get_by_type(LLMResponseReceivedEvent)
    assert len(llm_events) == 2

    requested = runtime.events.get_by_type(ToolRequestedEvent)
    assert len(requested) == 1
    assert requested[0].tool_name == "get_system_info"

    allowed_events = runtime.events.get_by_type(ToolAllowedEvent)
    assert len(allowed_events) == 1

    executed = runtime.events.get_by_type(ToolExecutedEvent)
    assert len(executed) == 1
    assert executed[0].success is True

    recorded = runtime.events.get_by_type(ObservationRecordedEvent)
    assert len(recorded) == 1

    completed = runtime.events.get_by_type(AgentCompletedEvent)
    assert len(completed) == 1


def test_unknown_tool_is_denied():
    llm_responses = [
        LLMResponse(
            content="",
            tool_calls=[{"id": "1", "tool_name": "unknown_tool", "arguments": {}}],
        ),
        LLMResponse(content="Done"),
    ]

    registry = ToolRegistry()
    registry.register(GetSystemInfoTool())

    policy = PolicyModel(
        organization_id=uuid4(),
        name="test",
        allowed_tool_ids=["get_system_info"],
    )
    llm = MockLLMProvider(llm_responses)
    evaluator = PolicyEvaluator(policy)
    runtime = AgentRuntime(llm=llm, registry=registry, policy=evaluator, max_iterations=10)
    agent = make_agent()

    asyncio_run(runtime.run("Test", agent, allowed_tool_identifiers=["get_system_info"]))

    denied = runtime.events.get_by_type(ToolDeniedEvent)
    assert len(denied) == 1
    assert denied[0].tool_name == "unknown_tool"
    assert "Unknown tool" in denied[0].reason


def test_policy_denied_tool():
    llm_responses = [
        LLMResponse(
            content="",
            tool_calls=[{"id": "1", "tool_name": "get_system_info", "arguments": {}}],
        ),
        LLMResponse(content="Done"),
    ]

    registry = ToolRegistry()
    registry.register(GetSystemInfoTool())

    policy = PolicyModel(
        organization_id=uuid4(),
        name="test",
        allowed_tool_ids=[],
    )

    llm = MockLLMProvider(llm_responses)
    evaluator = PolicyEvaluator(policy)
    runtime = AgentRuntime(llm=llm, registry=registry, policy=evaluator, max_iterations=10)
    agent = make_agent()

    asyncio_run(runtime.run("Test", agent, allowed_tool_identifiers=[]))

    denied = runtime.events.get_by_type(ToolDeniedEvent)
    assert len(denied) >= 1


def test_max_iterations_exceeded():
    llm_responses = [
        LLMResponse(
            content="",
            tool_calls=[{"id": "1", "tool_name": "get_system_info", "arguments": {}}],
        ),
    ] * 12

    tool = GetSystemInfoTool()
    registry = ToolRegistry()
    registry.register(tool)

    policy = PolicyModel(
        organization_id=uuid4(),
        name="test",
        allowed_tool_ids=["get_system_info"],
    )

    llm = MockLLMProvider(llm_responses)
    evaluator = PolicyEvaluator(policy)
    runtime = AgentRuntime(llm=llm, registry=registry, policy=evaluator, max_iterations=3)
    agent = make_agent()

    result = asyncio_run(runtime.run("Test", agent, allowed_tool_identifiers=["get_system_info"]))

    assert result.status == AgentStatus.MAX_ITERATIONS


def test_organization_context_propagation():
    org = Organization(name="Test Org")
    agent = Agent(
        organization_id=org.id,
        workspace_id=uuid4(),
        name="Agent",
        role="investigator",
        autonomy_level="read_only",
    )

    llm_responses = [LLMResponse(content="Done")]
    tool = GetSystemInfoTool()
    registry = ToolRegistry()
    registry.register(tool)
    policy = PolicyModel(
        organization_id=org.id,
        name="test",
        allowed_tool_ids=["get_system_info"],
    )
    llm = MockLLMProvider(llm_responses)
    evaluator = PolicyEvaluator(policy)
    runtime = AgentRuntime(llm=llm, registry=registry, policy=evaluator, max_iterations=10)

    result = asyncio_run(runtime.run("Test", agent, allowed_tool_identifiers=["get_system_info"]))

    assert result.organization_id == org.id
    assert result.agent_id == agent.id
    started = runtime.events.get_by_type(AgentStartedEvent)
    assert started[0].organization_id == org.id


def asyncio_run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)
