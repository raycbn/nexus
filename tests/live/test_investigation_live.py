import contextlib
from uuid import uuid4

import pytest
from packages.agent.llm.contract import LLMResponse, ToolCall
from packages.agent.llm.mock import MockLLMProvider
from packages.agent.runtime.events import (
    ToolExecutedEvent,
)
from packages.agent.runtime.runtime import AgentRuntime
from packages.agent.runtime.state import AgentStatus
from packages.connectors.factory import create_connector, register_linux_tools
from packages.domain.models.agent import Agent
from packages.domain.models.organization import Organization
from packages.domain.models.policy import Policy as PolicyModel
from packages.domain.models.resource import Resource
from packages.investigations.engine import InvestigationEngine
from packages.investigations.models import (
    HypothesisStatus,
)
from packages.mcp.client import MCPToolClient
from packages.mcp.server import NexusMCPServer
from packages.policies.evaluator import PolicyEvaluator
from packages.tools.registry import ToolRegistry

INFRASTRUCTURE_TOOL_IDS = [
    "get_system_info",
    "get_cpu_usage",
    "get_memory_usage",
    "get_disk_usage",
    "get_processes",
    "get_service_status",
]
VALIDATION_TOOL_ID = "get_application_health"
ALL_TOOL_IDS = [*INFRASTRUCTURE_TOOL_IDS, VALIDATION_TOOL_ID]


def _linux_resource() -> Resource:
    return Resource(
        organization_id=uuid4(),
        workspace_id=None,
        name="linux-lab-01",
        resource_type="linux_server",
    )


@pytest.fixture
async def linux_scenario():
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
        name="Linux Investigator",
        role="investigator",
        autonomy_level="read_only",
        allowed_tool_ids=[],
    )
    policy = PolicyModel(
        organization_id=org.id,
        name="linux-investigation-policy",
        allowed_tool_ids=[
            "get_system_info",
            "get_cpu_usage",
            "get_memory_usage",
            "get_disk_usage",
            "get_processes",
            "get_service_status",
            "get_application_health",
        ],
    )
    evaluator = PolicyEvaluator(policy)

    scenario = {
        "mcp_client": mcp_client,
        "connector": connector,
        "resource": resource,
        "runtime_registry": runtime_registry,
        "policy": evaluator,
        "agent": agent,
        "org": org,
    }

    yield scenario

    with contextlib.suppress(Exception):
        await mcp_client.disconnect()
    await connector.disconnect(resource)


@pytest.mark.live
class TestInvestigationLive:
    @pytest.mark.asyncio
    async def test_live_investigation_with_mock_llm(self, linux_scenario):
        scenario = linux_scenario

        collection_responses = [
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
            LLMResponse(
                content="",
                tool_calls=[ToolCall(id="5", tool_name="get_processes", arguments={})],
            ),
            LLMResponse(
                content="",
                tool_calls=[ToolCall(id="6", tool_name="get_service_status", arguments={})],
            ),
            LLMResponse(content="Infrastructure collected. Now validating application."),
        ]

        validation_responses = [
            LLMResponse(
                content="",
                tool_calls=[ToolCall(id="7", tool_name="get_application_health", arguments={})],
            ),
            LLMResponse(content="Application latency confirmed as root cause."),
        ]

        runtime = AgentRuntime(
            llm=MockLLMProvider([]),
            registry=scenario["runtime_registry"],
            policy=scenario["policy"],
            max_iterations=15,
        )

        engine = InvestigationEngine(
            runtime=runtime,
            agent=scenario["agent"],
            allowed_tool_identifiers=[
                "get_system_info",
                "get_cpu_usage",
                "get_memory_usage",
                "get_disk_usage",
                "get_processes",
                "get_service_status",
                "get_application_health",
            ],
        )

        # Phase 1: Collect infrastructure observations
        state1 = await engine.run_collection_phase(
            "Investigate why the API is slow.",
            collection_responses,
        )

        assert state1.status == AgentStatus.COMPLETED
        assert len(state1.tool_results) == 6
        assert len(engine.investigation.evidence) == 6

        # Form hypothesis
        hypothesis = engine.form_hypothesis(
            text="The API slowness is caused by the /api/slow endpoint latency.",
            supporting_evidence_ids=[str(e.id) for e in engine.investigation.evidence],
        )

        # Phase 2: Validation
        state2 = await engine.run_validation_phase(
            "Validate the hypothesis by checking application health and /api/slow latency.",
            validation_responses,
        )

        assert state2.status == AgentStatus.COMPLETED
        assert len(state2.tool_results) == 1

        validation_result = state2.tool_results[0].get("structured_content")
        assert validation_result is not None
        assert "slow_latency_seconds" in validation_result
        assert validation_result["slow_reproduced"] is True
        assert validation_result["slow_latency_seconds"] >= 1.5

        engine.validate_hypothesis(
            hypothesis=hypothesis,
            action_tool="get_application_health",
            expected_condition="/api/slow latency >= ~2 seconds",
            actual_result=validation_result,
            passed=validation_result.get("slow_reproduced", False),
        )

        assert hypothesis.status == HypothesisStatus.VALIDATED

        engine.conclude(
            finding=(
                "The API slowness is caused by the /api/slow endpoint "
                "which introduces ~2 second artificial delay."
            ),
            confidence=0.95,
            supporting_evidence_ids=[str(e.id) for e in engine.investigation.evidence],
            unresolved_uncertainty="No other infrastructure bottlenecks detected.",
        )

        assert engine.investigation.conclusion.confidence == 0.95
        assert engine.investigation.status == "completed"

        executed = runtime.events.get_by_type(ToolExecutedEvent)
        for e in executed:
            assert e.resource_mode == "real"
