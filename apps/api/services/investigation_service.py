import contextlib
from uuid import UUID, uuid4

from packages.agent.llm.contract import LLMResponse, ToolCall
from packages.agent.llm.mock import MockLLMProvider
from packages.agent.runtime.runtime import AgentRuntime
from packages.connectors.factory import create_connector, register_linux_tools
from packages.domain.models.agent import Agent
from packages.domain.models.policy import Policy as PolicyModel
from packages.domain.models.resource import Resource
from packages.investigations.engine import InvestigationEngine
from packages.investigations.models import Investigation
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


class InvestigationApplicationService:
    def __init__(self) -> None:
        self._resources: dict[UUID, Resource] = {}
        self._agents: dict[UUID, Agent] = {}
        self._policies: dict[UUID, PolicyModel] = {}

    async def run_investigation(self, objective: str) -> Investigation:
        """Run a full investigation using the real InvestigationEngine with Linux lab."""
        # Set up development resource and agent
        resource = self._get_or_create_resource()
        agent = self._get_or_create_agent()
        policy = self._get_or_create_policy()

        # Create connector and connect to Linux lab
        connector = create_connector(resource)
        await connector.connect(resource)

        try:
            # Set up MCP server and client
            server_registry = ToolRegistry()
            register_linux_tools(connector, server_registry)

            mcp_server = NexusMCPServer(name="nexus-linux-live", registry=server_registry)
            mcp_client = MCPToolClient(server_name="nexus-linux-live")
            await mcp_client.connect(mcp_server.server)

            try:
                discovered = await mcp_client.list_tools()
                runtime_registry = ToolRegistry()
                for tool_def in discovered:
                    runtime_registry.register(mcp_client.create_tool_wrapper(tool_def))

                evaluator = PolicyEvaluator(policy)

                # Build collection phase LLM responses
                collection_responses = self._build_collection_responses()

                # Build validation phase LLM responses
                validation_responses = self._build_validation_responses()

                runtime = AgentRuntime(
                    llm=MockLLMProvider(collection_responses),
                    registry=runtime_registry,
                    policy=evaluator,
                    max_iterations=15,
                )

                engine = InvestigationEngine(
                    runtime=runtime,
                    agent=agent,
                    allowed_tool_identifiers=ALL_TOOL_IDS,
                )

                # Phase 1: Collect infrastructure observations
                await engine.run_collection_phase(
                    objective,
                    collection_responses,
                )

                # Form hypothesis
                hypothesis = engine.form_hypothesis(
                    text="The API slowness is caused by the /api/slow endpoint latency.",
                    supporting_evidence_ids=[str(e.id) for e in engine.investigation.evidence],
                )

                # Phase 2: Validation with application health tool
                runtime._llm = MockLLMProvider(validation_responses)
                state2 = await engine.run_validation_phase(
                    "Validate the hypothesis by checking application health and /api/slow latency.",
                    validation_responses,
                )

                # Validate hypothesis
                validation_result = state2.tool_results[0].get("structured_content")
                engine.validate_hypothesis(
                    hypothesis=hypothesis,
                    action_tool=VALIDATION_TOOL_ID,
                    expected_condition="/api/slow latency >= ~2 seconds",
                    actual_result=validation_result,
                    passed=(
                        validation_result.get("slow_reproduced", False)
                        if validation_result
                        else False
                    ),
                )

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

                return engine.investigation

            finally:
                with contextlib.suppress(Exception):
                    await mcp_client.disconnect()
        finally:
            await connector.disconnect(resource)

    def _get_or_create_resource(self) -> Resource:
        org_id = uuid4()
        for resource in self._resources.values():
            if resource.name == "linux-lab-01":
                return resource

        resource = Resource(
            organization_id=org_id,
            workspace_id=None,
            name="linux-lab-01",
            resource_type="linux_server",
            environment="development",
            description="Local Linux lab for development",
            enabled=True,
            labels={"purpose": "development", "location": "local"},
        )
        self._resources[resource.id] = resource
        return resource

    def _get_or_create_agent(self) -> Agent:
        for agent in self._agents.values():
            if agent.name == "Linux Investigator":
                return agent

        agent = Agent(
            organization_id=uuid4(),
            workspace_id=None,
            name="Linux Investigator",
            role="investigator",
            description="Investigates Linux system issues",
            system_instructions="You are an expert Linux system investigator.",
            enabled=True,
            autonomy_level="read_only",
            allowed_tool_ids=[],
            policy_id=None,
        )
        self._agents[agent.id] = agent
        return agent

    def _get_or_create_policy(self) -> PolicyModel:
        for policy in self._policies.values():
            if policy.name == "linux-investigation-policy":
                return policy

        policy = PolicyModel(
            organization_id=uuid4(),
            name="linux-investigation-policy",
            allowed_tool_ids=ALL_TOOL_IDS,
        )
        self._policies[policy.id] = policy
        return policy

    def _build_collection_responses(self) -> list[LLMResponse]:
        """Build LLM responses for the collection phase."""
        responses: list[LLMResponse] = []
        for i, tool_name in enumerate(INFRASTRUCTURE_TOOL_IDS, 1):
            responses.append(
                LLMResponse(
                    content="",
                    tool_calls=[
                        ToolCall(
                            id=str(i),
                            tool_name=tool_name,
                            arguments={},
                        )
                    ],
                )
            )
        # Add application health tool call
        responses.append(
            LLMResponse(
                content="",
                tool_calls=[
                    ToolCall(
                        id=str(len(INFRASTRUCTURE_TOOL_IDS) + 1),
                        tool_name=VALIDATION_TOOL_ID,
                        arguments={},
                    )
                ],
            )
        )
        # Final response with conclusion
        responses.append(
            LLMResponse(
                content=(
                    "Investigation complete: API latency confirmed via /api/slow "
                    "endpoint with 5s delay. Infrastructure (CPU, memory, disk, "
                    "processes, services) all healthy. Root cause: artificial "
                    "delay in /api/slow endpoint."
                ),
            )
        )
        return responses

    def _build_validation_responses(self) -> list[LLMResponse]:
        """Build LLM responses for the validation phase."""
        return [
            LLMResponse(
                content="",
                tool_calls=[
                    ToolCall(
                        id="validation_1",
                        tool_name=VALIDATION_TOOL_ID,
                        arguments={},
                    )
                ],
            ),
            LLMResponse(
                content="Application latency confirmed as root cause via /api/slow endpoint.",
            ),
        ]
