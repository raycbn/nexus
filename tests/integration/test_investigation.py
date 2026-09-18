from typing import Any
from uuid import uuid4

import pytest
from packages.agent.llm.contract import LLMResponse, ToolCall
from packages.agent.llm.mock import MockLLMProvider
from packages.agent.runtime.runtime import AgentRuntime
from packages.agent.runtime.state import AgentStatus
from packages.connectors.factory import create_connector, register_linux_tools
from packages.domain.models.agent import Agent
from packages.domain.models.organization import Organization
from packages.domain.models.policy import Policy as PolicyModel
from packages.domain.models.resource import Resource
from packages.investigations.engine import InvestigationEngine
from packages.investigations.models import (
    Conclusion,
    Evidence,
    Hypothesis,
    HypothesisStatus,
    Investigation,
    InvestigationStatus,
    Validation,
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


def _slow_latency() -> str:
    return "2.05"


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
        return "15.2", 0
    if command.startswith("cat /proc/loadavg"):
        return "0.50 0.75 1.00 1/200 1234", 0
    if command.startswith("nproc"):
        return "4", 0
    if command.startswith("cat /proc/meminfo"):
        return (
            "MemTotal: 8192000 kB\n"
            "MemFree: 2048000 kB\n"
            "MemAvailable: 6144000 kB\n"
            "SwapTotal: 2048000 kB\n"
            "SwapFree: 1536000 kB\n"
        ), 0
    if command.startswith("df -h"):
        return (
            "Filesystem      Size  Used Avail Use% Mounted on\n"
            "/dev/sda1        50G   25G   25G  50% /\n"
        ), 0
    if "ps -eo" in command:
        return "123  nginx   0.5  1.2\n456  python3  2.1  3.4\n", 0
    if "ss -tlnp" in command:
        return (
            "State      Recv-Q Send-Q Local Address:Port               Peer Address:Port\n"
            "LISTEN     0      128    0.0.0.0:80                       0.0.0.0:*\n"
            "LISTEN     0      128    0.0.0.0:22                       0.0.0.0:*\n"
            "LISTEN     0      128    0.0.0.0:5000                     0.0.0.0:*\n"
        ), 0
    if "sshd" in command or "nginx" in command or "python3" in command:
        return "1", 0
    if "curl" in command and "/health" in command:
        return "200", 0
    if "curl" in command and "/api/status" in command:
        return "200", 0
    if "curl" in command and "/api/db" in command:
        return "200", 0
    if "curl" in command and "/api/redis" in command:
        return "200", 0
    if "curl" in command and "/api/slow" in command:
        return "2.05", 0
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


async def build_scenario(fake: FakeSSHConnection | None = None):
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
    wrappers: list[Any] = []
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
        allowed_tool_ids=ALL_TOOL_IDS,
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


class TestInvestigationEngine:
    @pytest.mark.asyncio
    async def test_complete_investigation_flow(self):
        scenario = await build_scenario()
        allowed = ALL_TOOL_IDS

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
            allowed_tool_identifiers=allowed,
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

        # Extract validation result
        validation_result = state2.tool_results[0].get("structured_content")
        assert validation_result is not None
        assert "slow_latency_seconds" in validation_result
        assert validation_result["slow_reproduced"] is True

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
        conclusion = engine.conclude(
            finding=(
                "The API slowness is caused by the /api/slow endpoint "
                "which introduces ~2 second artificial delay."
            ),
            confidence=0.95,
            supporting_evidence_ids=[str(e.id) for e in engine.investigation.evidence],
            unresolved_uncertainty="No other infrastructure bottlenecks detected.",
        )

        assert conclusion.confidence == 0.95
        assert engine.investigation.status == InvestigationStatus.COMPLETED

        await scenario["mcp_client"].disconnect()

    @pytest.mark.asyncio
    async def test_unresolved_hypothesis(self):
        scenario = await build_scenario()

        collection_responses = [
            LLMResponse(
                content="",
                tool_calls=[ToolCall(id="1", tool_name="get_system_info", arguments={})],
            ),
            LLMResponse(
                content="",
                tool_calls=[ToolCall(id="2", tool_name="get_cpu_usage", arguments={})],
            ),
            LLMResponse(content="CPU and system look normal."),
        ]

        validation_responses = [
            LLMResponse(
                content="",
                tool_calls=[ToolCall(id="3", tool_name="get_application_health", arguments={})],
            ),
            LLMResponse(content="Application health looks normal too."),
        ]

        runtime = AgentRuntime(
            llm=MockLLMProvider([]),
            registry=scenario["runtime_registry"],
            policy=scenario["policy"],
            max_iterations=10,
        )

        engine = InvestigationEngine(
            runtime=runtime,
            agent=scenario["agent"],
            allowed_tool_identifiers=ALL_TOOL_IDS,
        )

        await engine.run_collection_phase(
            "Investigate why the API is slow.",
            collection_responses,
        )

        hypothesis = engine.form_hypothesis(
            text="The API slowness might be caused by database contention.",
        )

        await engine.run_validation_phase(
            "Validate by checking application health.",
            validation_responses,
        )

        # Validation result shows no slow latency
        validation_result = {"slow_latency_seconds": 0.05, "slow_reproduced": False}

        engine.validate_hypothesis(
            hypothesis=hypothesis,
            action_tool=VALIDATION_TOOL_ID,
            expected_condition="/api/slow latency >= ~2 seconds",
            actual_result=validation_result,
            passed=False,
        )

        assert hypothesis.status == HypothesisStatus.CONTRADICTED

        conclusion = engine.conclude(
            finding=(
                "Application health check shows no latency on /api/slow. Root cause not identified."
            ),
            confidence=0.4,
            supporting_evidence_ids=[],
            unresolved_uncertainty="Need deeper application-level tracing.",
        )

        assert conclusion.confidence == 0.4
        assert hypothesis.status == HypothesisStatus.CONTRADICTED

        await scenario["mcp_client"].disconnect()

    @pytest.mark.asyncio
    async def test_evidence_creation_from_tool_results(self):
        scenario = await build_scenario()

        llm_responses = [
            LLMResponse(
                content="",
                tool_calls=[ToolCall(id="1", tool_name="get_system_info", arguments={})],
            ),
            LLMResponse(content="done"),
        ]

        runtime = AgentRuntime(
            llm=MockLLMProvider(llm_responses),
            registry=scenario["runtime_registry"],
            policy=scenario["policy"],
            max_iterations=5,
        )

        await runtime.run("Check system", scenario["agent"], allowed_tool_identifiers=ALL_TOOL_IDS)

        evidence = Evidence(
            source_tool="get_system_info",
            resource_id=scenario["resource"].id,
            observed_value={"hostname": "linux-lab-01"},
            mode="real",
            relevance=1.0,
        )

        assert evidence.source_tool == "get_system_info"
        assert evidence.resource_id == scenario["resource"].id
        assert evidence.observed_value == {"hostname": "linux-lab-01"}
        assert evidence.mode == "real"
        assert evidence.relevance == 1.0

        await scenario["mcp_client"].disconnect()

    @pytest.mark.asyncio
    async def test_hypothesis_creation_and_status(self):
        hypothesis = Hypothesis(text="Test hypothesis")
        assert hypothesis.status == HypothesisStatus.PROPOSED
        assert hypothesis.supporting_evidence_ids == []

        hypothesis.status = HypothesisStatus.SUPPORTED
        assert hypothesis.status == HypothesisStatus.SUPPORTED

    @pytest.mark.asyncio
    async def test_validation_passed(self):
        validation = Validation(
            action_tool="get_application_health",
            expected_condition="latency >= 2s",
            actual_result={"slow_latency_seconds": 2.05, "slow_reproduced": True},
            passed=True,
        )
        assert validation.passed is True

    @pytest.mark.asyncio
    async def test_investigation_lifecycle(self):
        investigation = Investigation(objective="Test objective")
        assert investigation.status == InvestigationStatus.STARTED
        assert investigation.evidence == []

        evidence = Evidence(source_tool="test_tool", observed_value={"test": "value"})
        investigation.add_evidence(evidence)
        assert len(investigation.evidence) == 1

        hypothesis = Hypothesis(text="Test hypothesis")
        investigation.add_hypothesis(hypothesis)
        assert len(investigation.hypotheses) == 1

        validation = Validation(
            action_tool="test", expected_condition="test", actual_result={}, passed=True
        )
        investigation.add_validation(validation)
        assert len(investigation.validations) == 1

        conclusion = Conclusion(
            finding="Test finding",
            confidence=0.8,
            supporting_evidence_ids=[evidence.id],
        )
        investigation.set_conclusion(conclusion)

        assert investigation.status == InvestigationStatus.COMPLETED
        assert investigation.completed_at is not None
        assert investigation.conclusion == conclusion
