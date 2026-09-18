from uuid import uuid4

import pytest


def _ollama_host() -> str:
    from packages.domain.config import NexusSettings

    settings = NexusSettings()
    return f"http://{settings.ollama_host}:{settings.ollama_port}"


def _ollama_available() -> bool:
    host = _ollama_host()
    try:
        import httpx

        response = httpx.get(f"{host}/", timeout=5)
        return response.status_code in (200, 404)
    except Exception:
        return False


def _model_available(model: str | None) -> bool:
    if model is None:
        return False

    host = _ollama_host()
    try:
        import httpx

        response = httpx.get(f"{host}/api/tags", timeout=10)
        models = response.json().get("models", [])
        return any(m.get("name") == model for m in models)
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _ollama_available(),
    reason="Ollama not available at configured host",
)


@pytest.mark.live
@pytest.mark.asyncio
async def test_ollama_live_basic_chat():
    from packages.agent.llm.contract import LLMMessage, LLMRequest
    from packages.agent.llm.ollama import OllamaProvider
    from packages.domain.config import NexusSettings

    settings = NexusSettings()
    model = settings.ollama_model

    if model is None:
        pytest.skip("OLLAMA_MODEL is not configured. Set it in .env or environment.")
    if not _model_available(model):
        pytest.skip(f"Ollama model '{model}' is not available.")

    provider = OllamaProvider(timeout=600)
    response = await provider.generate(
        LLMRequest(
            messages=[LLMMessage(role="user", content="Say hello in one sentence")],
            tools=[],
        )
    )
    assert response.content


@pytest.mark.live
@pytest.mark.asyncio
async def test_ollama_live_tool_call():
    from packages.agent.llm.contract import LLMMessage, LLMRequest
    from packages.agent.llm.ollama import OllamaProvider
    from packages.domain.config import NexusSettings
    from packages.tools.providers.mock_tools import GetSystemInfoTool
    from packages.tools.registry import ToolRegistry

    settings = NexusSettings()
    model = settings.ollama_model

    if model is None:
        pytest.skip("OLLAMA_MODEL is not configured. Set it in .env or environment.")
    if not _model_available(model):
        pytest.skip(f"Ollama model '{model}' is not available.")

    registry = ToolRegistry()
    registry.register(GetSystemInfoTool())
    provider = OllamaProvider(registry=registry, timeout=600)
    response = await provider.generate(
        LLMRequest(
            messages=[LLMMessage(role="user", content="What is the system hostname?")],
            tools=["get_system_info"],
        )
    )
    if response.tool_calls:
        assert response.tool_calls[0].tool_name == "get_system_info"
    else:
        assert response.content


@pytest.mark.live
@pytest.mark.asyncio
async def test_ollama_live_e2e_agent_loop():
    from packages.agent.llm.ollama import OllamaProvider
    from packages.agent.runtime.events import (
        LLMResponseReceivedEvent,
        ObservationRecordedEvent,
        ToolExecutedEvent,
        ToolRequestedEvent,
    )
    from packages.agent.runtime.runtime import AgentRuntime
    from packages.domain.config import NexusSettings
    from packages.domain.models.agent import Agent
    from packages.domain.models.organization import Organization
    from packages.domain.models.policy import Policy as PolicyModel
    from packages.policies.evaluator import PolicyEvaluator
    from packages.tools.providers.mock_tools import GetSystemInfoTool
    from packages.tools.registry import ToolRegistry

    settings = NexusSettings()
    model = settings.ollama_model

    if model is None:
        pytest.skip("OLLAMA_MODEL is not configured. Set it in .env or environment.")
    if not _model_available(model):
        pytest.skip(f"Ollama model '{model}' is not available.")

    org = Organization(name="CLI Demo")
    agent = Agent(
        organization_id=org.id,
        workspace_id=uuid4(),
        name="CLI Agent",
        role="investigator",
        autonomy_level="read_only",
        allowed_tool_ids=[],
    )

    registry = ToolRegistry()
    registry.register(GetSystemInfoTool())

    policy = PolicyModel(
        organization_id=org.id,
        name="cli-policy",
        allowed_tool_ids=["get_system_info"],
    )
    evaluator = PolicyEvaluator(policy)
    llm = OllamaProvider(registry=registry, timeout=600)
    runtime = AgentRuntime(
        llm=llm,
        registry=registry,
        policy=evaluator,
        max_iterations=10,
    )

    result = await runtime.run(
        "Use the get_system_info tool to find the system hostname, then"
        " report the hostname in your final answer.",
        agent,
        allowed_tool_identifiers=["get_system_info"],
    )

    llm_count = len(runtime.events.get_by_type(LLMResponseReceivedEvent))
    tool_requested = False
    tool_executed = False
    observation_recorded = False
    tool_call_count = 0

    for event in runtime.events.events:
        if isinstance(event, ToolRequestedEvent):
            tool_requested = True
            assert event.tool_name == "get_system_info"
            tool_call_count += 1
        elif isinstance(event, ToolExecutedEvent):
            if event.success:
                tool_executed = True
        elif isinstance(event, ObservationRecordedEvent):
            observation_recorded = True

    assert tool_requested, "get_system_info was not requested"
    assert tool_executed, "get_system_info was not executed"
    assert observation_recorded, "Observation was not recorded"
    assert llm_count >= 2, f"Expected at least 2 LLM generations, got {llm_count}"
    assert result.final_result, "No final result was produced"
    assert "</think>" not in (result.final_result or ""), (
        "Final result contains hidden reasoning tags"
    )
