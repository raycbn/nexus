import json

import httpx
import pytest
from packages.agent.llm.contract import LLMMessage, LLMRateLimitError, LLMRequest
from packages.agent.llm.openai_compatible import OpenAICompatibleProvider


@pytest.mark.asyncio
async def test_openai_compatible_sends_messages_and_parses_tool_calls() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["authorization"] = request.headers["Authorization"]
        seen["json"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": "",
                            "reasoning": "diagnosing",
                            "tool_calls": [
                                {
                                    "id": "call-1",
                                    "function": {
                                        "name": "linux.shell",
                                        "arguments": '{"command":"uptime"}',
                                    },
                                }
                            ],
                        }
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    original = httpx.AsyncClient

    def client_factory(*args: object, **kwargs: object) -> httpx.AsyncClient:
        kwargs["transport"] = transport
        return original(*args, **kwargs)

    httpx.AsyncClient = client_factory  # type: ignore[assignment]
    try:
        provider = OpenAICompatibleProvider(
            base_url="https://example.test/v1",
            api_key="test-key",
            model="test-model",
        )
        response = await provider.generate(
            LLMRequest(messages=[LLMMessage(role="user", content="check system")])
        )
    finally:
        httpx.AsyncClient = original

    assert seen["url"] == "https://example.test/v1/chat/completions"
    assert seen["authorization"] == "Bearer test-key"
    assert response.thinking == "diagnosing"
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].tool_name == "linux.shell"
    assert response.tool_calls[0].arguments == {"command": "uptime"}

@pytest.mark.asyncio
async def test_openai_compatible_maps_429_to_rate_limit_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            headers={"Retry-After": "2.5"},
            json={"error": {"message": "rate limited"}},
        )

    transport = httpx.MockTransport(handler)
    original = httpx.AsyncClient

    def client_factory(*args: object, **kwargs: object) -> httpx.AsyncClient:
        kwargs["transport"] = transport
        return original(*args, **kwargs)

    httpx.AsyncClient = client_factory  # type: ignore[assignment]
    try:
        provider = OpenAICompatibleProvider(
            base_url="https://example.test/v1",
            api_key="test-key",
            model="test-model",
        )
        with pytest.raises(LLMRateLimitError) as exc_info:
            await provider.generate(
                LLMRequest(messages=[LLMMessage(role="user", content="hello")])
            )
    finally:
        httpx.AsyncClient = original

    assert exc_info.value.retry_after == 2.5
