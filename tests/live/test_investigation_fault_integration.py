import contextlib
import time

import pytest
from packages.connectors.factory import create_connector, register_linux_tools
from packages.domain.models.agent import Agent
from packages.domain.models.organization import Organization
from packages.domain.models.policy import Policy as PolicyModel
from packages.domain.models.resource import Resource
from packages.fault_injection import FaultScenarioId, get_registry
from packages.investigations.models import HypothesisStatus
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


@pytest.fixture
async def linux_scenario():
    """Set up Linux lab with real SSH and MCP"""
    resource = Resource(
        organization_id=__import__("uuid").uuid4(),
        workspace_id=None,
        name="linux-lab-01",
        resource_type="linux_server",
    )
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
        workspace_id=__import__("uuid").uuid4(),
        name="Linux Investigator",
        role="investigator",
        autonomy_level="read_only",
        allowed_tool_ids=[],
    )
    policy = PolicyModel(
        organization_id=org.id,
        name="linux-investigation-policy",
        allowed_tool_ids=ALL_TOOL_IDS,
    )
    evaluator = PolicyEvaluator(policy)

    yield {
        "mcp_client": mcp_client,
        "connector": connector,
        "resource": resource,
        "runtime_registry": runtime_registry,
        "policy": evaluator,
        "agent": agent,
        "org": org,
    }

    with contextlib.suppress(Exception):
        await mcp_client.disconnect()
    await connector.disconnect(resource)


@pytest.mark.live
class TestInvestigationWithFaultInjection:
    @pytest.mark.asyncio
    async def test_investigation_with_api_latency(self, linux_scenario):
        """Test investigation with api_latency fault injected"""
        scenario_data = linux_scenario

        # Activate api_latency fault
        fault_registry = get_registry()
        fault_result = fault_registry.activate(FaultScenarioId.API_LATENCY)
        assert fault_result.success is True

        try:
            # Run investigation with fault active
            collection_responses = [
                __import__(
                    "packages.agent.llm.contract", fromlist=["LLMResponse", "ToolCall"]
                ).LLMResponse(
                    content="",
                    tool_calls=[
                        __import__("packages.agent.llm.contract", fromlist=["ToolCall"]).ToolCall(
                            id="1", tool_name="get_system_info", arguments={}
                        )
                    ],
                ),
                __import__(
                    "packages.agent.llm.contract", fromlist=["LLMResponse", "ToolCall"]
                ).LLMResponse(
                    content="",
                    tool_calls=[
                        __import__("packages.agent.llm.contract", fromlist=["ToolCall"]).ToolCall(
                            id="2", tool_name="get_cpu_usage", arguments={}
                        )
                    ],
                ),
                __import__(
                    "packages.agent.llm.contract", fromlist=["LLMResponse", "ToolCall"]
                ).LLMResponse(
                    content="",
                    tool_calls=[
                        __import__("packages.agent.llm.contract", fromlist=["ToolCall"]).ToolCall(
                            id="3", tool_name="get_memory_usage", arguments={}
                        )
                    ],
                ),
                __import__(
                    "packages.agent.llm.contract", fromlist=["LLMResponse", "ToolCall"]
                ).LLMResponse(
                    content="",
                    tool_calls=[
                        __import__("packages.agent.llm.contract", fromlist=["ToolCall"]).ToolCall(
                            id="4", tool_name="get_disk_usage", arguments={}
                        )
                    ],
                ),
                __import__(
                    "packages.agent.llm.contract", fromlist=["LLMResponse", "ToolCall"]
                ).LLMResponse(
                    content="",
                    tool_calls=[
                        __import__("packages.agent.llm.contract", fromlist=["ToolCall"]).ToolCall(
                            id="5", tool_name="get_processes", arguments={}
                        )
                    ],
                ),
                __import__(
                    "packages.agent.llm.contract", fromlist=["LLMResponse", "ToolCall"]
                ).LLMResponse(
                    content="",
                    tool_calls=[
                        __import__("packages.agent.llm.contract", fromlist=["ToolCall"]).ToolCall(
                            id="6", tool_name="get_service_status", arguments={}
                        )
                    ],
                ),
                __import__(
                    "packages.agent.llm.contract", fromlist=["LLMResponse", "ToolCall"]
                ).LLMResponse(
                    content="",
                    tool_calls=[
                        __import__("packages.agent.llm.contract", fromlist=["ToolCall"]).ToolCall(
                            id="7", tool_name="get_application_health", arguments={}
                        )
                    ],
                ),
__import__("packages.agent.llm.contract", fromlist=["LLMResponse"]).LLMResponse(
                    content=(
                        "Investigation complete: API latency confirmed via /api/slow "
                        "endpoint with 5s delay. Infrastructure (CPU, memory, disk, "
                        "processes, services) all healthy. Root cause: artificial "
                        "delay in /api/slow endpoint."
                    ),
                ),
            ]

            runtime = __import__(
                "packages.agent.runtime.runtime", fromlist=["AgentRuntime"]
            ).AgentRuntime(
                llm=__import__(
                    "packages.agent.llm.mock", fromlist=["MockLLMProvider"]
                ).MockLLMProvider(collection_responses),
                registry=scenario_data["runtime_registry"],
                policy=scenario_data["policy"],
                max_iterations=15,
            )

            engine = __import__(
                "packages.investigations.engine", fromlist=["InvestigationEngine"]
            ).InvestigationEngine(
                runtime=runtime,
                agent=scenario_data["agent"],
                allowed_tool_identifiers=ALL_TOOL_IDS,
            )

            # Phase 1: Collect infrastructure observations
            state1 = await engine.run_collection_phase(
                "Investigate why the API is slow.",
                collection_responses,
            )

            assert state1.status.value == "completed"
            assert len(state1.tool_results) == 7  # 6 infrastructure + 1 application health
            assert len(engine.investigation.evidence) == 7

            # Form hypothesis
            hypothesis = engine.form_hypothesis(
                text="The API slowness is caused by the /api/slow endpoint latency.",
                supporting_evidence_ids=[str(e.id) for e in engine.investigation.evidence],
            )

            # Phase 2: Validation with application health tool
            validation_responses = [
                __import__(
                    "packages.agent.llm.contract", fromlist=["LLMResponse", "ToolCall"]
                ).LLMResponse(
                    content="",
                    tool_calls=[
                        __import__("packages.agent.llm.contract", fromlist=["ToolCall"]).ToolCall(
                            id="8", tool_name="get_application_health", arguments={}
                        )
                    ],
                ),
                __import__("packages.agent.llm.contract", fromlist=["LLMResponse"]).LLMResponse(
                    content="Application latency confirmed as root cause via /api/slow endpoint.",
                ),
            ]

            state2 = await engine.run_validation_phase(
                "Validate the hypothesis by checking application health and /api/slow latency.",
                validation_responses,
            )

            assert state2.status.value == "completed"
            assert len(state2.tool_results) == 1

            validation_result = state2.tool_results[0].get("structured_content")
            assert validation_result is not None
            assert "slow_latency_seconds" in validation_result
            assert validation_result["slow_reproduced"] is True
            assert validation_result["slow_latency_seconds"] >= 1.5

            # Validate hypothesis
            engine.validate_hypothesis(
                hypothesis=hypothesis,
                action_tool=VALIDATION_TOOL_ID,
                expected_condition="/api/slow latency >= ~2 seconds",
                actual_result=validation_result,
                passed=validation_result.get("slow_reproduced", False),
            )

            assert hypothesis.status == HypothesisStatus.VALIDATED

            # Conclude
            engine.conclude(
                finding=(
                    "The API slowness is caused by the /api/slow endpoint "
                    "which introduces ~5 second artificial delay."
                ),
                confidence=0.95,
                supporting_evidence_ids=[str(e.id) for e in engine.investigation.evidence],
                unresolved_uncertainty="No other infrastructure bottlenecks detected.",
            )

            assert engine.investigation.conclusion.confidence == 0.95
            assert engine.investigation.status.value == "completed"

            # Verify fault was active during investigation
            executed = runtime.events.get_by_type(
                __import__(
                    "packages.agent.runtime.events", fromlist=["ToolExecutedEvent"]
                ).ToolExecutedEvent
            )
            for e in executed:
                assert e.resource_mode == "real"

        finally:
            # Clean up fault
            fault_registry = get_registry()
            fault_registry.deactivate("api_latency")


@pytest.mark.live
class TestInvestigationFaultCleanup:
    """Ensure fault scenarios are cleaned up after investigation"""

    @pytest.mark.asyncio
    async def test_fault_cleanup_after_investigation(self, linux_scenario):
        fault_registry = get_registry()

        # Ensure clean state
        for sid in ["api_latency", "api_failure", "redis_unavailable", "postgres_unavailable"]:
            get_registry().deactivate(sid)
        time.sleep(1)

        fault_registry.activate("api_latency")
        assert get_registry().is_active("api_latency")

        # Deactivate
        get_registry().deactivate("api_latency")
        time.sleep(1)
        assert not get_registry().is_active("api_latency")
