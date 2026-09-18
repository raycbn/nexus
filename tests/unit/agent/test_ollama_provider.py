from unittest.mock import AsyncMock, patch

import pytest
from packages.agent.llm.contract import LLMMessage, LLMRequest
from packages.agent.llm.ollama import OllamaProvider
from packages.tools.providers.mock_tools import GetSystemInfoTool
from packages.tools.registry import ToolRegistry


def test_ollama_provider_has_host_and_model():
    provider = OllamaProvider(host="localhost", model="test-model")
    assert provider._host == "localhost"
    assert provider._model == "test-model"
    assert provider._base_url == "http://localhost:11434"


def test_ollama_provider_raises_without_model(monkeypatch):
    monkeypatch.setattr(
        "packages.agent.llm.ollama.NexusSettings",
        lambda: type(
            "Settings",
            (),
            {
                "ollama_host": "localhost",
                "ollama_port": 11434,
                "ollama_model": None,
                "ollama_think": False,
                "ollama_num_ctx": 8192,
                "ollama_timeout": 120,
            },
        )(),
    )
    with pytest.raises(RuntimeError, match="OLLAMA_MODEL"):
        OllamaProvider()


def test_ollama_provider_uses_explicit_model():
    provider = OllamaProvider(model="hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M")
    assert provider._model == "hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M"


def test_ollama_provider_accepts_registry():
    registry = ToolRegistry()
    registry.register(GetSystemInfoTool())
    provider = OllamaProvider(host="localhost", model="test-model", registry=registry)
    assert provider._registry is registry


def test_ollama_provider_resolves_tool_from_registry():
    registry = ToolRegistry()
    registry.register(GetSystemInfoTool())
    provider = OllamaProvider(host="localhost", model="test-model", registry=registry)
    result = provider._resolve_tool("get_system_info")
    assert result is not None
    assert result.get_identifier() == "get_system_info"


def test_ollama_provider_returns_none_for_unknown_tool():
    provider = OllamaProvider(host="localhost", model="test-model")
    result = provider._resolve_tool("nonexistent")
    assert result is None


def test_ollama_provider_stores_think_false_by_default():
    provider = OllamaProvider(host="localhost", model="test-model")
    assert provider._think is False


def test_ollama_provider_stores_num_ctx():
    provider = OllamaProvider(host="localhost", model="test-model")
    assert provider._num_ctx == 8192


def test_ollama_provider_stores_timeout():
    provider = OllamaProvider(host="localhost", model="test-model")
    assert provider._timeout == 120


def test_ollama_provider_accepts_custom_timeout():
    provider = OllamaProvider(host="localhost", model="test-model", timeout=300)
    assert provider._timeout == 300


@pytest.mark.asyncio
async def test_ollama_provider_sends_think_in_request():
    provider = OllamaProvider(host="localhost", model="test-model")

    mock_client = AsyncMock()
    mock_client.chat.return_value = {
        "message": {"role": "assistant", "content": "Hello"},
    }

    with patch.object(provider, "_ensure_client", return_value=mock_client):
        await provider.generate(
            LLMRequest(messages=[LLMMessage(role="user", content="Hi")], tools=[])
        )

    _, kwargs = mock_client.chat.call_args
    assert "think" in kwargs
    assert kwargs["think"] is False


@pytest.mark.asyncio
async def test_ollama_provider_sends_num_ctx_in_request():
    provider = OllamaProvider(host="localhost", model="test-model")

    mock_client = AsyncMock()
    mock_client.chat.return_value = {
        "message": {"role": "assistant", "content": "Hello"},
    }

    with patch.object(provider, "_ensure_client", return_value=mock_client):
        await provider.generate(
            LLMRequest(messages=[LLMMessage(role="user", content="Hi")], tools=[])
        )

    _, kwargs = mock_client.chat.call_args
    assert "options" in kwargs
    assert kwargs["options"] == {"num_ctx": 8192}


@pytest.mark.asyncio
async def test_ollama_provider_resolves_tools_via_registry():
    registry = ToolRegistry()
    registry.register(GetSystemInfoTool())
    provider = OllamaProvider(host="localhost", model="test-model", registry=registry)

    mock_client = AsyncMock()
    mock_client.chat.return_value = {
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call-1",
                    "function": {"name": "get_system_info", "arguments": "{}"},
                }
            ],
        }
    }

    with patch.object(provider, "_ensure_client", return_value=mock_client):
        response = await provider.generate(
            LLMRequest(
                messages=[LLMMessage(role="user", content="Check system")],
                tools=["get_system_info"],
            )
        )

    assert response.tool_calls[0].tool_name == "get_system_info"
    assert response.tool_calls[0].arguments == {}

    _, kwargs = mock_client.chat.call_args
    tools_sent = kwargs.get("tools")
    assert tools_sent is not None
    assert len(tools_sent) == 1
    assert tools_sent[0]["function"]["name"] == "get_system_info"
