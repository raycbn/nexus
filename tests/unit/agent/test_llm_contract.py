import asyncio

import pytest
from packages.agent.llm.contract import LLMRequest, LLMResponse, ToolCall
from packages.agent.llm.mock import MockLLMProvider


def test_mock_provider_returns_scripted_responses():
    responses = [
        LLMResponse(content="Response 1"),
        LLMResponse(content="Response 2"),
    ]
    provider = MockLLMProvider(responses)

    loop = asyncio.new_event_loop()
    result1 = loop.run_until_complete(provider.generate(LLMRequest(messages=[])))
    assert result1.content == "Response 1"

    result2 = loop.run_until_complete(provider.generate(LLMRequest(messages=[])))
    assert result2.content == "Response 2"
    loop.close()


def test_mock_provider_tracks_calls():
    provider = MockLLMProvider([LLMResponse(content="test")])

    loop = asyncio.new_event_loop()
    loop.run_until_complete(provider.generate(LLMRequest(messages=[])))
    assert provider.call_count == 1
    assert len(provider.call_log) == 1
    loop.close()


def test_mock_provider_exhausted_raises():
    provider = MockLLMProvider([LLMResponse(content="only one")])

    loop = asyncio.new_event_loop()
    loop.run_until_complete(provider.generate(LLMRequest(messages=[])))
    with pytest.raises(RuntimeError):
        loop.run_until_complete(provider.generate(LLMRequest(messages=[])))
    loop.close()


def test_mock_provider_reset():
    provider = MockLLMProvider([LLMResponse(content="test")])

    loop = asyncio.new_event_loop()
    loop.run_until_complete(provider.generate(LLMRequest(messages=[])))
    assert provider.call_count == 1
    provider.reset()
    assert provider.call_count == 0
    loop.close()


def test_llm_response_is_final_answer_without_tool_calls():
    response = LLMResponse(content="Hello")
    assert response.is_final_answer is True
    assert response.wants_tool_execution is False


def test_llm_response_requests_tool_with_tool_calls():
    response = LLMResponse(
        content="",
        tool_calls=[ToolCall(id="1", tool_name="get_info", arguments={})],
    )
    assert response.is_final_answer is False
    assert response.wants_tool_execution is True


def test_llm_response_with_both_content_and_tool_calls():
    response = LLMResponse(
        content="thinking",
        tool_calls=[ToolCall(id="1", tool_name="get_info", arguments={})],
    )
    assert response.is_final_answer is False
    assert response.wants_tool_execution is True
