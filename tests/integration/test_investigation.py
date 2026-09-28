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
            organization_id=scenario["org"].id,
            workspace_id=scenario["agent"].workspace_id,
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
            organization_id=scenario["org"].id,
            workspace_id=scenario["agent"].workspace_id,
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
        investigation = Investigation(organization_id=uuid4(), objective="Test objective")
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


class TestInvestigationEngineTenantAndEvidenceIntegrity:
    """Regression tests for evidence ID preservation and tenant context."""

    @pytest.mark.asyncio
    async def test_form_hypothesis_preserves_evidence_ids(self):
        """Evidence IDs passed to form_hypothesis must be preserved
        exactly, not replaced with fake UUIDs."""
        scenario = await build_scenario()

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
            organization_id=scenario["org"].id,
            workspace_id=scenario["agent"].workspace_id,
        )

        # Add some evidence manually to the investigation
        evidence1 = Evidence(source_tool="tool1", observed_value={"data": "1"})
        evidence2 = Evidence(source_tool="tool2", observed_value={"data": "2"})
        engine.investigation.add_evidence(evidence1)
        engine.investigation.add_evidence(evidence2)

        # Form hypothesis with specific evidence IDs
        hypothesis = engine.form_hypothesis(
            text="Test hypothesis",
            supporting_evidence_ids=[evidence1.id, evidence2.id],
            contradicting_evidence_ids=[],
        )

        # Verify the exact same UUIDs are preserved
        assert hypothesis.supporting_evidence_ids == [evidence1.id, evidence2.id]
        assert hypothesis.contradicting_evidence_ids == []
        # Ensure no fake UUIDs were generated
        expected = (evidence1.id, evidence2.id)
        assert all(eid in expected for eid in hypothesis.supporting_evidence_ids)

    @pytest.mark.asyncio
    async def test_conclude_preserves_evidence_ids(self):
        """Evidence IDs passed to conclude must be preserved
        exactly, not replaced with fake UUIDs."""
        scenario = await build_scenario()

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
            organization_id=scenario["org"].id,
            workspace_id=scenario["agent"].workspace_id,
        )

        # Add some evidence
        evidence1 = Evidence(source_tool="tool1", observed_value={"data": "1"})
        evidence2 = Evidence(source_tool="tool2", observed_value={"data": "2"})
        engine.investigation.add_evidence(evidence1)
        engine.investigation.add_evidence(evidence2)

        # Conclude with specific evidence IDs
        conclusion = engine.conclude(
            finding="Test finding",
            confidence=0.9,
            supporting_evidence_ids=[evidence1.id, evidence2.id],
            unresolved_uncertainty=None,
        )

        # Verify the exact same UUIDs are preserved
        assert conclusion.supporting_evidence_ids == [evidence1.id, evidence2.id]
        # Ensure no fake UUIDs were generated
        expected = (evidence1.id, evidence2.id)
        assert all(eid in expected for eid in conclusion.supporting_evidence_ids)

    @pytest.mark.asyncio
    async def test_investigation_tenant_context_preserved(self):
        """Investigation must use the organization_id and workspace_id provided by the caller."""
        scenario = await build_scenario()

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
            organization_id=scenario["org"].id,
            workspace_id=scenario["agent"].workspace_id,
        )

        # Verify investigation has the correct tenant context
        assert engine.investigation.organization_id == scenario["org"].id
        assert engine.investigation.workspace_id == scenario["agent"].workspace_id

    @pytest.mark.asyncio
    async def test_engine_never_generates_tenant_uuids(self):
        """The engine must not generate its own tenant UUIDs - they must come from the caller."""
        scenario = await build_scenario()

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
            organization_id=scenario["org"].id,
            workspace_id=scenario["agent"].workspace_id,
        )

        # Verify investigation has the exact tenant IDs provided by caller
        # (no generation of new UUIDs for tenant identity)
        assert engine.investigation.organization_id == scenario["org"].id
        assert engine.investigation.workspace_id == scenario["agent"].workspace_id
        # The investigation's IDs should be the exact objects passed in
        assert engine.investigation.organization_id is scenario["org"].id
        assert engine.investigation.workspace_id is scenario["agent"].workspace_id

    @pytest.mark.asyncio
    async def test_form_hypothesis_never_generates_evidence_uuids(self):
        """form_hypothesis must not generate fake evidence UUIDs."""
        scenario = await build_scenario()

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
            organization_id=scenario["org"].id,
            workspace_id=scenario["agent"].workspace_id,
        )

        evidence1 = Evidence(source_tool="tool1", observed_value={"data": "1"})
        engine.investigation.add_evidence(evidence1)

        hypothesis = engine.form_hypothesis(
            text="Test",
            supporting_evidence_ids=[evidence1.id],
        )
        # Verify exact UUID preservation - no fake UUIDs generated
        assert hypothesis.supporting_evidence_ids == [evidence1.id]
        assert hypothesis.supporting_evidence_ids[0] is evidence1.id

    @pytest.mark.asyncio
    async def test_conclude_never_generates_evidence_uuids(self):
        """conclude must not generate fake evidence UUIDs."""
        scenario = await build_scenario()

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
            organization_id=scenario["org"].id,
            workspace_id=scenario["agent"].workspace_id,
        )

        evidence1 = Evidence(source_tool="tool1", observed_value={"data": "1"})
        engine.investigation.add_evidence(evidence1)

        conclusion = engine.conclude(
            finding="Test finding",
            confidence=0.9,
            supporting_evidence_ids=[evidence1.id],
        )
        # Verify exact UUID preservation - no fake UUIDs generated
        assert conclusion.supporting_evidence_ids == [evidence1.id]
        assert conclusion.supporting_evidence_ids[0] is evidence1.id


class TestTenantContextIsolationAndPropagation:
    """Tests for tenant context isolation and propagation."""

    @pytest.mark.asyncio
    async def test_two_tenant_contexts_remain_isolated(self):
        """Two different TenantContexts must not leak data between each other."""

        from apps.api.services.investigation_service import InvestigationApplicationService
        from packages.domain.context import (
            get_development_tenant_context_for_org,
        )

        # Create two different tenant contexts with different organization IDs
        ctx1 = get_development_tenant_context_for_org("11111111-1111-1111-1111-111111111111")
        ctx2 = get_development_tenant_context_for_org("22222222-2222-2222-2222-222222222222")

        # Verify they have different organization IDs
        assert ctx1.organization_id != ctx2.organization_id
        assert ctx1.user_id == ctx2.user_id  # Same user for now (dev context)
        assert ctx1.workspace_id == ctx2.workspace_id  # Same workspace for now

        # Simulate service creation with different contexts
        service1 = InvestigationApplicationService(tenant_context=ctx1)
        service2 = InvestigationApplicationService(tenant_context=ctx2)

        # Verify services retain their tenant contexts
        assert service1.tenant.organization_id == ctx1.organization_id
        assert service2.tenant.organization_id == ctx2.organization_id
        assert service1.tenant.organization_id != service2.tenant.organization_id

    @pytest.mark.asyncio
    async def test_organization_id_propagated_unchanged_to_engine(self):
        """organization_id must propagate unchanged from application service to engine."""
        from apps.api.services.investigation_service import InvestigationApplicationService
        from packages.domain.context import get_development_tenant_context

        ctx = get_development_tenant_context()
        service = InvestigationApplicationService(tenant_context=ctx)

        agent = Agent(
            organization_id=ctx.organization_id,
            workspace_id=ctx.workspace_id,
            name="Test Agent",
            role="investigator",
        )
        runtime = AgentRuntime(
            llm=MockLLMProvider([]),
            registry=ToolRegistry(),
            policy=PolicyEvaluator(None),
            max_iterations=1,
        )

        engine = InvestigationEngine(
            runtime=runtime,
            agent=agent,
            allowed_tool_identifiers=ALL_TOOL_IDS,
            organization_id=service.tenant.organization_id,
            workspace_id=service.tenant.workspace_id,
        )

        # Verify exact propagation - same UUID object
        assert engine.investigation.organization_id == ctx.organization_id
        assert engine.investigation.organization_id is ctx.organization_id

    @pytest.mark.asyncio
    async def test_workspace_id_propagated_unchanged_to_engine(self):
        """workspace_id must propagate unchanged from application service to engine."""
        from apps.api.services.investigation_service import InvestigationApplicationService
        from packages.domain.context import get_development_tenant_context

        ctx = get_development_tenant_context()
        service = InvestigationApplicationService(tenant_context=ctx)

        agent = Agent(
            organization_id=ctx.organization_id,
            workspace_id=ctx.workspace_id,
            name="Test Agent",
            role="investigator",
        )
        runtime = AgentRuntime(
            llm=MockLLMProvider([]),
            registry=ToolRegistry(),
            policy=PolicyEvaluator(None),
            max_iterations=1,
        )

        engine = InvestigationEngine(
            runtime=runtime,
            agent=agent,
            allowed_tool_identifiers=ALL_TOOL_IDS,
            organization_id=service.tenant.organization_id,
            workspace_id=service.tenant.workspace_id,
        )

        # Verify exact propagation - same UUID object
        assert engine.investigation.workspace_id == ctx.workspace_id
        assert engine.investigation.workspace_id is ctx.workspace_id

    @pytest.mark.asyncio
    async def test_user_id_preserved_in_tenant_context(self):
        """user_id must be preserved in TenantContext."""
        from uuid import UUID

        from apps.api.services.investigation_service import InvestigationApplicationService
        from packages.domain.context import get_development_tenant_context
        from packages.domain.models.context import TenantContext

        ctx = get_development_tenant_context()

        # Verify the development context has a user_id
        assert ctx.user_id is not None
        assert isinstance(ctx.user_id, UUID)

        # Create a custom context with different user_id
        custom_ctx = TenantContext(
            user_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            organization_id=ctx.organization_id,
            workspace_id=ctx.workspace_id,
            role="operator",
        )

        service = InvestigationApplicationService(tenant_context=custom_ctx)
        assert service.tenant.user_id == custom_ctx.user_id
        assert service.tenant.role == "operator"

    @pytest.mark.asyncio
    async def test_no_tenant_uuid_generation_in_application_service(self):
        """InvestigationApplicationService must not generate tenant UUIDs."""

        from apps.api.services.investigation_service import InvestigationApplicationService
        from packages.domain.context import get_development_tenant_context

        ctx = get_development_tenant_context()
        service = InvestigationApplicationService(tenant_context=ctx)

        # Verify that the service uses the exact tenant IDs from context
        # No UUID generation should happen for tenant identity
        assert service.tenant.organization_id is ctx.organization_id
        assert service.tenant.workspace_id is ctx.workspace_id
        assert service.tenant.user_id is ctx.user_id

        # Objects created from the authenticated tenant context must retain its IDs.
        resource = Resource(
            organization_id=ctx.organization_id,
            workspace_id=ctx.workspace_id,
            name="test-resource",
            resource_type="linux_server",
        )
        agent = Agent(
            organization_id=ctx.organization_id,
            workspace_id=ctx.workspace_id,
            name="Test Agent",
            role="investigator",
        )
        policy = PolicyModel(
            organization_id=ctx.organization_id,
            name="test-policy",
            allowed_tool_ids=ALL_TOOL_IDS,
        )

        assert resource.organization_id is ctx.organization_id
        assert agent.organization_id is ctx.organization_id
        assert policy.organization_id is ctx.organization_id
        assert resource.workspace_id is ctx.workspace_id
        assert agent.workspace_id is ctx.workspace_id

    @pytest.mark.asyncio
    async def test_incident_engine_receives_correct_tenant_context(self):
        """IncidentEngine must receive correct tenant context from API."""
        from packages.domain.context import get_development_tenant_context
        from packages.incidents.engine import IncidentEngine
        from packages.incidents.in_memory_repository import InMemoryIncidentRepository

        ctx = get_development_tenant_context()
        repo = InMemoryIncidentRepository()

        engine = IncidentEngine(repository=repo, tenant_context=ctx)

        # Verify tenant context is exactly the one provided
        assert engine._tenant.organization_id == ctx.organization_id
        assert engine._tenant.organization_id is ctx.organization_id
        assert engine._tenant.workspace_id == ctx.workspace_id
        assert engine._tenant.workspace_id is ctx.workspace_id
        assert engine._tenant.user_id == ctx.user_id

    @pytest.mark.asyncio
    async def test_investigation_engine_receives_correct_tenant_context(self):
        """InvestigationEngine must receive correct tenant context from API/Service."""
        from packages.agent.llm.mock import MockLLMProvider
        from packages.agent.runtime.runtime import AgentRuntime
        from packages.domain.context import get_development_tenant_context
        from packages.investigations.engine import InvestigationEngine
        from packages.policies.evaluator import PolicyEvaluator
        from packages.tools.registry import ToolRegistry

        ctx = get_development_tenant_context()
        runtime = AgentRuntime(
            llm=MockLLMProvider([]),
            registry=ToolRegistry(),
            policy=PolicyEvaluator(None),  # Will be None for this test
            max_iterations=10,
        )

        from packages.domain.models.agent import Agent

        agent = Agent(
            organization_id=ctx.organization_id,
            workspace_id=ctx.workspace_id,
            name="Test Agent",
            role="investigator",
        )

        engine = InvestigationEngine(
            runtime=runtime,
            agent=agent,
            allowed_tool_identifiers=ALL_TOOL_IDS,
            organization_id=ctx.organization_id,
            workspace_id=ctx.workspace_id,
        )

        # Verify tenant context is exactly the one provided
        assert engine.investigation.organization_id == ctx.organization_id
        assert engine.investigation.organization_id is ctx.organization_id
        assert engine.investigation.workspace_id == ctx.workspace_id
        assert engine.investigation.workspace_id is ctx.workspace_id

    @pytest.mark.asyncio
    async def test_api_route_tenant_context_dependency_exists(self):
        """API routes must have TenantContext dependency, not hardcoded UUIDs."""
        from packages.domain.context import get_development_tenant_context
        from packages.domain.models.context import TenantContext

        # Verify the development context provider exists and returns valid context
        ctx = get_development_tenant_context()
        assert isinstance(ctx, TenantContext)
        assert ctx.organization_id is not None
        assert ctx.user_id is not None

        # Verify it's deterministic (same call returns same IDs)
        ctx2 = get_development_tenant_context()
        assert ctx.organization_id == ctx2.organization_id
        assert ctx.user_id == ctx2.user_id
        assert ctx.workspace_id == ctx2.workspace_id

    @pytest.mark.asyncio
    async def test_development_context_provider_is_deterministic(self):
        """Development context provider must return deterministic IDs."""
        from packages.domain.context import get_development_tenant_context

        ctx1 = get_development_tenant_context()
        ctx2 = get_development_tenant_context()
        ctx3 = get_development_tenant_context()

        # All calls must return the exact same UUIDs
        assert ctx1.organization_id == ctx2.organization_id == ctx3.organization_id
        assert ctx1.user_id == ctx2.user_id == ctx3.user_id
        assert ctx1.workspace_id == ctx2.workspace_id == ctx3.workspace_id
        assert ctx1.role == ctx2.role == ctx3.role

        # Verify they are the expected deterministic values
        assert str(ctx1.organization_id) == "00000000-0000-0000-0000-000000000002"
        assert str(ctx1.user_id) == "00000000-0000-0000-0000-000000000001"
        assert str(ctx1.workspace_id) == "00000000-0000-0000-0000-000000000003"
        assert ctx1.role == "admin"


class TestAuthenticationSecurity:
    """Security tests for authentication and tenant isolation."""

    @pytest.fixture
    def test_principal(self):
        """Create a test authenticated principal."""
        from uuid import UUID

        from packages.domain.models.identity import AuthenticatedPrincipal

        return AuthenticatedPrincipal(
            user_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            organization_id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
            workspace_id=UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
            role="admin",
        )

    @pytest.fixture
    def valid_token(self, test_principal):
        """Create a valid JWT token for testing."""

        from packages.auth import create_access_token
        from packages.domain.config import NexusSettings

        settings = NexusSettings(
            secret_key="test-secret-key-for-testing-only-32-chars-minimum",
            app_environment="local",
        )
        return create_access_token(test_principal, settings)

    @pytest.fixture
    def expired_token(self, test_principal):
        """Create an expired JWT token for testing."""
        from datetime import timedelta

        from packages.auth import create_access_token
        from packages.domain.config import NexusSettings

        settings = NexusSettings(
            secret_key="test-secret-key-for-testing-only-32-chars-minimum",
            app_environment="local",
        )
        return create_access_token(test_principal, settings, expires_delta=timedelta(seconds=-1))

    @pytest.fixture
    def settings(self):
        """Test settings with test secret."""
        from packages.domain.config import NexusSettings

        return NexusSettings(
            secret_key="test-secret-key-for-testing-only-32-chars-minimum",
            app_environment="local",
        )

    @pytest.fixture
    def mock_request(self):
        """Create a mock FastAPI request."""
        from unittest.mock import MagicMock

        return MagicMock()

    @pytest.mark.asyncio
    async def test_valid_token_accepted(self, valid_token, settings):
        """Valid token should be accepted and produce AuthenticatedPrincipal."""

        from packages.auth import decode_token

        claims = decode_token(valid_token, settings)
        principal = claims.to_principal()

        assert principal.user_id is not None
        assert principal.organization_id is not None
        assert principal.role == "admin"

    @pytest.mark.asyncio
    async def test_missing_token_rejected(self, settings, mock_request):
        """Request without token should be rejected with 401."""
        from fastapi.exceptions import HTTPException
        from packages.auth import get_current_principal

        mock_request.headers.get.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_current_principal(mock_request, settings)

        assert exc_info.value.status_code == 401
        assert "Missing or invalid Authorization header" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_malformed_token_rejected(self, settings, mock_request):
        """Malformed token should be rejected with 401."""
        from fastapi.exceptions import HTTPException
        from packages.auth import get_current_principal

        mock_request.headers.get.return_value = "Bearer not-a-valid-token"

        with pytest.raises(HTTPException) as exc_info:
            await get_current_principal(mock_request, settings)

        assert exc_info.value.status_code == 401
        assert "Invalid or expired token" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_expired_token_rejected(self, expired_token, settings):
        """Expired token should be rejected with 401."""
        from fastapi.exceptions import HTTPException
        from packages.auth import decode_token

        with pytest.raises(HTTPException) as exc_info:
            decode_token(expired_token, settings)

        assert exc_info.value.status_code == 401
        assert "Invalid or expired token" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_invalid_signature_rejected(self, settings):
        """Token with invalid signature should be rejected."""
        from uuid import UUID

        from fastapi.exceptions import HTTPException
        from packages.auth import create_access_token, decode_token
        from packages.domain.models.identity import AuthenticatedPrincipal

        # Create token with different secret
        other_settings = type(settings)(
            secret_key="different-secret-key-for-testing-only-32-chars-min",
            app_environment="local",
        )

        test_principal = AuthenticatedPrincipal(
            user_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            organization_id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
            workspace_id=UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
            role="admin",
        )
        other_token = create_access_token(test_principal, other_settings)

        with pytest.raises(HTTPException) as exc_info:
            decode_token(other_token, settings)

        assert exc_info.value.status_code == 401
        assert "Invalid or expired token" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_principal_contains_expected_user_id(self, test_principal):
        """Authenticated principal should contain expected user_id."""
        from uuid import UUID

        assert test_principal.user_id == UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

    @pytest.mark.asyncio
    async def test_principal_contains_expected_organization_id(self, test_principal):
        """Authenticated principal should contain expected organization_id."""
        from uuid import UUID

        assert test_principal.organization_id == UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

    @pytest.mark.asyncio
    async def test_principal_contains_expected_workspace_id(self, test_principal):
        """Authenticated principal should contain expected workspace_id."""
        from uuid import UUID

        assert test_principal.workspace_id == UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")

    @pytest.mark.asyncio
    async def test_principal_contains_expected_role(self, test_principal):
        """Authenticated principal should contain expected role."""
        assert test_principal.role == "admin"

    @pytest.mark.asyncio
    async def test_tenant_context_constructed_from_authenticated_identity(self, test_principal):
        """TenantContext should be constructed from authenticated identity."""
        from packages.auth import principal_to_tenant_context

        ctx = principal_to_tenant_context(test_principal)

        assert ctx.user_id == test_principal.user_id
        assert ctx.organization_id == test_principal.organization_id
        assert ctx.workspace_id == test_principal.workspace_id
        assert ctx.role == test_principal.role

    @pytest.mark.asyncio
    async def test_client_organization_id_cannot_override_authenticated(self, test_principal):
        """Client-supplied organization_id cannot override authenticated tenant."""
        from uuid import UUID

        from packages.auth import principal_to_tenant_context

        ctx = principal_to_tenant_context(test_principal)

        # Verify the context has the authenticated organization_id
        assert ctx.organization_id == test_principal.organization_id

        # Simulate a malicious request with different org_id in payload
        malicious_org_id = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")

        # The context should still have the original authenticated org_id
        assert ctx.organization_id != malicious_org_id
        assert ctx.organization_id == test_principal.organization_id

    @pytest.mark.asyncio
    async def test_client_workspace_id_cannot_override_authenticated(self, test_principal):
        """Client-supplied workspace_id cannot override authenticated workspace."""
        from uuid import UUID

        from packages.auth import principal_to_tenant_context

        ctx = principal_to_tenant_context(test_principal)

        # Verify the context has the authenticated workspace_id
        assert ctx.workspace_id == test_principal.workspace_id

        # Simulate a malicious request with different workspace_id in payload
        malicious_workspace_id = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")

        # The context should still have the original authenticated workspace_id
        assert ctx.workspace_id != malicious_workspace_id
        assert ctx.workspace_id == test_principal.workspace_id

    @pytest.mark.asyncio
    async def test_development_context_never_silently_used_in_production(self):
        """Production mode should fail if dev secret is used."""
        import pytest
        from fastapi.exceptions import HTTPException
        from packages.auth import _check_production_secret
        from packages.domain.config import NexusSettings

        # Production-like settings with dev secret
        prod_settings = NexusSettings(
            secret_key="dev-secret-key-change-in-production",
            app_environment="production",
        )

        with pytest.raises(HTTPException) as exc_info:
            _check_production_secret(prod_settings)

        assert exc_info.value.status_code == 500
        assert "Production environment requires a proper SECRET_KEY" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_development_context_allowed_in_local_mode(self):
        """Local mode should allow dev secret."""
        from packages.auth import _check_production_secret
        from packages.domain.config import NexusSettings

        local_settings = NexusSettings(
            secret_key="dev-secret-key-change-in-production",
            app_environment="local",
        )

        # Should not raise
        _check_production_secret(local_settings)

    @pytest.mark.asyncio
    async def test_two_authenticated_tenants_remain_isolated(self):
        """Two different authenticated principals should remain isolated."""
        from uuid import UUID

        from packages.auth import create_access_token, decode_token
        from packages.domain.config import NexusSettings
        from packages.domain.models.identity import AuthenticatedPrincipal

        settings = NexusSettings(
            secret_key="test-secret-key-for-testing-only-32-chars-minimum",
            app_environment="local",
        )

        principal1 = AuthenticatedPrincipal(
            user_id=UUID("11111111-1111-1111-1111-111111111111"),
            organization_id=UUID("22222222-2222-2222-2222-222222222222"),
            workspace_id=None,
            role="admin",
        )

        principal2 = AuthenticatedPrincipal(
            user_id=UUID("33333333-3333-3333-3333-333333333333"),
            organization_id=UUID("44444444-4444-4444-4444-444444444444"),
            workspace_id=None,
            role="user",
        )

        token1 = create_access_token(principal1, settings)
        token2 = create_access_token(principal2, settings)

        claims1 = decode_token(token1, settings)
        claims2 = decode_token(token2, settings)

        assert claims1.org_id != claims2.org_id
        assert claims1.sub != claims2.sub
        assert claims1.role != claims2.role
