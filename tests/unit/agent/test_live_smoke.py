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
