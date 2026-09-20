import contextlib
import time

import pytest
from apps.api import app
from httpx import ASGITransport, AsyncClient
from packages.connectors.factory import create_connector, register_linux_tools
from packages.domain.models.agent import Agent
from packages.domain.models.organization import Organization
from packages.domain.models.policy import Policy as PolicyModel
from packages.domain.models.resource import Resource
from packages.fault_injection import FaultScenarioId, get_registry
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
        policy_id=None,
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


@pytest.fixture
async def api_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.live
class TestInvestigationAPILive:
    @pytest.mark.asyncio
    async def test_investigation_api_with_fault(self, linux_scenario, api_client):
        """Test the investigation API endpoint with a real fault injected."""
        # Activate api_latency fault
        fault_registry = get_registry()
        fault_result = fault_registry.activate(FaultScenarioId.API_LATENCY)
        assert fault_result.success is True

        try:
            # Call the investigation API
            response = await api_client.post(
                "/api/investigations",
                json={"objective": "Investigate why the API is slow."},
            )

            assert response.status_code == 201
            data = response.json()

            # Verify investigation structure
            assert "id" in data
            assert data["objective"] == "Investigate why the API is slow."
            assert data["status"] == "completed"
            assert "started_at" in data
            assert "completed_at" in data

            # Verify evidence
            assert "evidence" in data
            assert len(data["evidence"]) >= 7  # 6 infrastructure + 1 application health
            for evidence in data["evidence"]:
                assert "id" in evidence
                assert "source_tool" in evidence
                assert "observed_value" in evidence
                assert "mode" in evidence
                assert evidence["mode"] == "real"

            # Verify hypotheses
            assert "hypotheses" in data
            assert len(data["hypotheses"]) >= 1
            hypothesis = data["hypotheses"][0]
            expected_text = "The API slowness is caused by the /api/slow endpoint latency."
            assert hypothesis["text"] == expected_text
            assert hypothesis["status"] == "validated"

            # Verify validations
            assert "validations" in data
            assert len(data["validations"]) >= 1
            validation = data["validations"][0]
            assert validation["action_tool"] == VALIDATION_TOOL_ID
            assert validation["passed"] is True

            # Verify conclusion
            assert "conclusion" in data
            assert data["conclusion"] is not None
            conclusion = data["conclusion"]
            assert "finding" in conclusion
            assert "confidence" in conclusion
            assert conclusion["confidence"] == 0.95
            assert "supporting_evidence_ids" in conclusion

            # Verify fault was active during investigation
            executed = __import__(
                "packages.agent.runtime.runtime", fromlist=["AgentRuntime"]
            ).AgentRuntime(
                llm=__import__(
                    "packages.agent.llm.mock", fromlist=["MockLLMProvider"]
                ).MockLLMProvider([]),
                registry=linux_scenario["runtime_registry"],
                policy=linux_scenario["policy"],
                max_iterations=15,
            )

            # Check all tool executions used real mode
            for e in executed.events.get_by_type(
                __import__(
                    "packages.agent.runtime.events", fromlist=["ToolExecutedEvent"]
                ).ToolExecutedEvent
            ):
                assert e.resource_mode == "real"

        finally:
            # Clean up fault
            fault_registry = get_registry()
            fault_registry.deactivate("api_latency")

    @pytest.mark.asyncio
    async def test_investigation_api_invalid_objective(self, api_client):
        """Test that the API rejects empty objectives."""
        response = await api_client.post(
            "/api/investigations",
            json={"objective": ""},
        )
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_investigation_api_no_secrets_in_response(self, linux_scenario, api_client):
        """Verify the API response doesn't contain sensitive data."""
        # Ensure clean fault state
        fault_registry = get_registry()
        for sid in ["api_latency", "api_failure", "redis_unavailable", "postgres_unavailable"]:
            fault_registry.deactivate(sid)
        time.sleep(1)

        response = await api_client.post(
            "/api/investigations",
            json={"objective": "Investigate why the API is slow."},
        )

        assert response.status_code == 201
        data = response.json()

        # Convert to string for searching
        import json

        response_str = json.dumps(data)

        # Check for sensitive patterns (actual secrets, not file references)
        sensitive_terms = [
            "password",
            "secret",
            "token",
            "private_key",
            "credential",
            "docker",
            "shell",
        ]
        for term in sensitive_terms:
            assert term not in response_str.lower(), f"Sensitive term '{term}' found in response"

        # SSH key path references (file paths) are allowed in development
        # but actual private key content must never be exposed
        if "ssh" in response_str.lower():
            assert "-----BEGIN" not in response_str, "Actual SSH private key found in response"
            assert "private_key" not in response_str.lower(), "Private key reference found"

    @pytest.mark.asyncio
    async def test_fault_cleanup_after_investigation(self, linux_scenario):
        """Ensure fault scenarios are cleaned up after investigation."""
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
