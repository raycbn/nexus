import asyncio
import sys
from uuid import uuid4

from packages.agent.runtime.runtime import AgentRuntime
from packages.domain.config import NexusSettings
from packages.domain.models.agent import Agent
from packages.domain.models.organization import Organization
from packages.domain.models.policy import Policy as PolicyModel
from packages.policies.evaluator import PolicyEvaluator
from packages.tools.providers.mock_tools import (
    GetCpuUsageTool,
    GetDiskUsageTool,
    GetMemoryUsageTool,
    GetRunningProcessesTool,
    GetSystemInfoTool,
)
from packages.tools.registry import ToolRegistry


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.nexus_agent <objective>", file=sys.stderr)
        return 1

    objective = " ".join(sys.argv[1:])

    settings = NexusSettings()
    print(f"Ollama host: {settings.ollama_base_url}")
    print(f"Ollama model: {settings.ollama_model}")
    print(f"Objective: {objective}")
    print()

    org = Organization(name="CLI Demo")
    agent = Agent(
        organization_id=org.id,
        workspace_id=uuid4(),
        name="CLI Agent",
        role="investigator",
        autonomy_level="read_only",
        allowed_tool_ids=[],
    )

    tools = [
        GetSystemInfoTool(),
        GetCpuUsageTool(),
        GetMemoryUsageTool(),
        GetDiskUsageTool(),
        GetRunningProcessesTool(),
    ]

    allowed_identifiers = [t.get_identifier() for t in tools]

    registry = ToolRegistry()
    for t in tools:
        registry.register(t)

    policy = PolicyModel(
        organization_id=org.id,
        name="cli-policy",
        allowed_tool_ids=allowed_identifiers,
    )
    evaluator = PolicyEvaluator(policy)

    from packages.agent.llm.ollama import OllamaProvider

    llm = OllamaProvider(registry=registry)

    runtime = AgentRuntime(
        llm=llm,
        registry=registry,
        policy=evaluator,
        max_iterations=10,
    )

    print("[AGENT] Starting")
    print()

    try:
        result = asyncio.run(
            runtime.run(objective, agent, allowed_tool_identifiers=allowed_identifiers)
        )
    except Exception as e:
        print(f"Runtime failed: {e}", file=sys.stderr)
        return 1

    print()
    print("=" * 60)
    print("AGENT RESULT")
    print("=" * 60)
    print(f"Status: {result.status}")
    print(f"Iterations: {result.iteration_count}")
    print()

    if runtime.events:
        from packages.agent.runtime.events import (
            AgentCompletedEvent,
            AgentFailedEvent,
            AgentStartedEvent,
            LLMResponseReceivedEvent,
            ObservationRecordedEvent,
            ToolAllowedEvent,
            ToolDeniedEvent,
            ToolExecutedEvent,
            ToolRequestedEvent,
        )

        started = runtime.events.get_by_type(AgentStartedEvent)
        if started:
            print("[AGENT] Starting")

        for event in runtime.events.events:
            if isinstance(event, AgentStartedEvent):
                print("[AGENT] Starting")
            elif isinstance(event, LLMResponseReceivedEvent):
                duration_s = f"{event.duration:.3f}s"
                print(f"[LLM] Response received ({duration_s})")
                if event.tool_call_count > 0:
                    print(f"[LLM] Tool calls: {event.tool_call_count}")
            elif isinstance(event, ToolRequestedEvent):
                print(f"[TOOL] Requested: {event.tool_name}")
            elif isinstance(event, ToolAllowedEvent):
                print(f"[POLICY] Allowed: {event.tool_name}")
            elif isinstance(event, ToolDeniedEvent):
                print(f"[POLICY] Denied: {event.tool_name} - {event.reason}")
            elif isinstance(event, ToolExecutedEvent):
                duration_s = f"{event.duration:.3f}s"
                print(f"[TOOL] Completed: {event.tool_name} ({duration_s})")
            elif isinstance(event, ObservationRecordedEvent):
                pass
            elif isinstance(event, AgentCompletedEvent):
                print("[AGENT] Completed")
                if event.final_result:
                    print(f"[AGENT] Final answer: {event.final_result}")
            elif isinstance(event, AgentFailedEvent):
                print(f"[AGENT] Failed: {event.reason}")

    if result.status.value in ("failed", "max_iterations"):
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
