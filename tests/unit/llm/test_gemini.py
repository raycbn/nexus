import json

import httpx
import pytest
from packages.agent.llm.contract import LLMMessage, LLMRequest
from packages.agent.llm.gemini import GeminiProvider
from packages.tools.providers.mock_tools import GetCpuUsageTool
from packages.tools.registry import ToolRegistry


def _mock_client(monkeypatch, handler):
    transport = httpx.MockTransport(handler)
    original = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)


@pytest.mark.asyncio
async def test_gemini_health_check_uses_official_model_endpoint(monkeypatch):
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["api_key"] = request.headers["x-goog-api-key"]
        return httpx.Response(200, json={"name": "models/gemini-3.8-flash"})

    _mock_client(monkeypatch, handler)
    provider = GeminiProvider(api_key="test-key")
    assert await provider.health_check() is True
    assert seen["url"].endswith("/models/gemini-3.8-flash")
    assert seen["api_key"] == "test-key"


@pytest.mark.asyncio
async def test_gemini_detect_capabilities_reads_model_limits(monkeypatch):
    def handler(request):
        return httpx.Response(
            200,
            json={
                "name": "models/gemini-3.8-flash",
                "inputTokenLimit": 1048576,
                "outputTokenLimit": 65536,
                "supportedGenerationMethods": ["generateContent"],
            },
        )

    _mock_client(monkeypatch, handler)
    provider = GeminiProvider(api_key="test-key")
    capabilities = await provider.detect_capabilities()

    assert capabilities["available"] is True
    assert capabilities["tool_calling"] is True
    assert capabilities["reasoning"] is True
    assert capabilities["structured_output"] is True
    assert capabilities["context_window_tokens"] == 1048576
    assert capabilities["output_token_limit"] == 65536


@pytest.mark.asyncio
async def test_gemini_normalizes_nexus_json_response_format(monkeypatch):
    seen = {}

    def handler(request):
        seen["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"ok":true}'}}]},
        )

    _mock_client(monkeypatch, handler)
    provider = GeminiProvider(api_key="test-key")
    response = await provider.generate(
        LLMRequest(
            messages=[LLMMessage(role="user", content="return json")],
            response_format="json",
        )
    )

    assert response.content == '{"ok":true}'
    assert seen["payload"]["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_gemini_inherits_tool_calling_from_common_adapter(monkeypatch):
    seen = {}

    def handler(request):
        seen["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": "",
                            "tool_calls": [
                                {
                                    "id": "call-1",
                                    "function": {
                                        "name": "get_cpu_usage",
                                        "arguments": "{}",
                                    },
                                }
                            ],
                        }
                    }
                ]
            },
        )

    _mock_client(monkeypatch, handler)
    registry = ToolRegistry()
    registry.register(GetCpuUsageTool())
    provider = GeminiProvider(api_key="test-key", registry=registry)
    response = await provider.generate(
        LLMRequest(
            messages=[LLMMessage(role="user", content="inspect cpu")],
            tools=["get_cpu_usage"],
        )
    )

    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].tool_name == "get_cpu_usage"
    assert seen["payload"]["tools"][0]["type"] == "function"
