import asyncio
from uuid import uuid4

from packages.agent.llm.contract import LLMResponse
from packages.agent.llm.mock import MockLLMProvider
from packages.agent.runtime.events import (
    AgentCompletedEvent,
    AgentStartedEvent,
    LLMResponseReceivedEvent,
)
from packages.agent.runtime.runtime import AgentRuntime
from packages.agent.runtime.state import AgentState, AgentStatus
from packages.domain.models.agent import Agent
from packages.domain.models.organization import Organization
from packages.domain.models.policy import Policy as PolicyModel
from packages.policies.evaluator import PolicyEvaluator
from packages.tools.providers.mock_tools import GetSystemInfoTool
from packages.tools.registry import ToolRegistry


def make_test_agent():
    org = Organization(name="Test")
    return Agent(
        organization_id=org.id,
        workspace_id=uuid4(),
        name="Test Agent",
        role="investigator",
        autonomy_level="read_only",
        allowed_tool_ids=[],
    )


def make_simple_runtime(responses, tools=None, max_iter=10):
    tool_list = tools or [GetSystemInfoTool()]
    registry = ToolRegistry()
    for t in tool_list:
        registry.register(t)
    policy = PolicyModel(
        organization_id=uuid4(),
        name="test",
        allowed_tool_ids=["get_system_info"],
    )
    evaluator = PolicyEvaluator(policy)
    llm = MockLLMProvider(responses)
    runtime = AgentRuntime(llm=llm, registry=registry, policy=evaluator, max_iterations=max_iter)
    return runtime, registry


def test_agent_state_has_required_fields():
    agent = make_test_agent()
    state = AgentState(
        objective="Investigate CPU",
        agent_id=agent.id,
        organization_id=agent.organization_id,
        workspace_id=agent.workspace_id,
    )
    assert state.objective == "Investigate CPU"
    assert state.agent_id == agent.id
    assert state.organization_id == agent.organization_id
    assert state.status == AgentStatus.PENDING
    assert state.iteration_count == 0
    assert state.messages == []
    assert state.tool_calls == []
    assert state.observations == []
    assert state.final_result is None


def test_agent_state_starts_as_pending():
    state = AgentState(
        objective="Test",
        agent_id=uuid4(),
        organization_id=uuid4(),
    )
    assert state.status == AgentStatus.PENDING


def test_agent_state_has_tool_methods():
    tool = GetSystemInfoTool()
    asyncio_run(tool.execute({}))


def test_runtime_executes_final_answer_in_one_step():
    responses = [
        LLMResponse(content="Investigation complete"),
    ]
    runtime, _registry = make_simple_runtime(responses, max_iter=10)
    agent = make_test_agent()
    result = asyncio_run(
        runtime.run("Investigate", agent, allowed_tool_identifiers=["get_system_info"])
    )
    assert result.status == AgentStatus.COMPLETED
    assert result.final_result == "Investigation complete"
    assert result.iteration_count == 0


def test_runtime_fails_when_llm_raises():
    class FailingLLM:
        async def generate(self, request):
            raise RuntimeError("LLM failure")

    tool_list = [GetSystemInfoTool()]
    registry = ToolRegistry()
    for t in tool_list:
        registry.register(t)
    policy = PolicyModel(
        organization_id=uuid4(),
        name="test",
        allowed_tool_ids=["get_system_info"],
    )
    evaluator = PolicyEvaluator(policy)
    llm = FailingLLM()
    runtime = AgentRuntime(llm=llm, registry=registry, policy=evaluator, max_iterations=10)
    agent = make_test_agent()
    result = asyncio_run(runtime.run("Test", agent, allowed_tool_identifiers=["get_system_info"]))
    assert result.status == AgentStatus.FAILED


def test_runtime_emits_agent_started_event():
    runtime, _ = make_simple_runtime([LLMResponse(content="done")])
    agent = make_test_agent()
    asyncio_run(runtime.run("Test", agent, allowed_tool_identifiers=["get_system_info"]))
    started_events = runtime.events.get_by_type(AgentStartedEvent)
    assert len(started_events) == 1
    assert started_events[0].agent_id == agent.id


def test_runtime_emits_agent_completed_event():
    runtime, _ = make_simple_runtime([LLMResponse(content="done")])
    agent = make_test_agent()
    asyncio_run(runtime.run("Test", agent, allowed_tool_identifiers=["get_system_info"]))
    completed_events = runtime.events.get_by_type(AgentCompletedEvent)
    assert len(completed_events) == 1


def test_runtime_emits_llm_response_events():
    runtime, _registry = make_simple_runtime(
        [
            LLMResponse(
                content="step 1",
                tool_calls=[{"id": "1", "tool_name": "get_system_info", "arguments": {}}],
            ),
            LLMResponse(content="done"),
        ]
    )
    agent = make_test_agent()
    asyncio_run(runtime.run("Test", agent, allowed_tool_identifiers=["get_system_info"]))
    llm_events = runtime.events.get_by_type(LLMResponseReceivedEvent)
    assert len(llm_events) == 2


def test_runtime_uses_max_iterations_default():
    runtime, _registry = make_simple_runtime([LLMResponse(content="done")], max_iter=5)
    assert runtime._max_iterations == 5


def asyncio_run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)
