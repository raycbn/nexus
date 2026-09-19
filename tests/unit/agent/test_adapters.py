from packages.agent.llm.adapter import ToolSchemaAdapter
from packages.agent.llm.contract import LLMMessage, ToolCall
from packages.agent.llm.message_adapter import OllamaMessageAdapter
from packages.tools.providers.mock_tools import GetSystemInfoTool


def make_tool():
    return GetSystemInfoTool()


class TestToolSchemaAdapter:
    def test_single_tool_conversion(self):
        tool = GetSystemInfoTool()
        schema = ToolSchemaAdapter.to_ollama_tool(tool)
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "get_system_info"
        assert (
            schema["function"]["description"] == "Returns system information for a target resource"
        )
        assert "parameters" in schema["function"]

    def test_multiple_tool_conversion(self):
        tools = [GetSystemInfoTool()]
        schemas = ToolSchemaAdapter.to_ollama_tools(tools)
        assert len(schemas) == 1
        assert schemas[0]["function"]["name"] == "get_system_info"

    def test_empty_tool_list(self):
        schemas = ToolSchemaAdapter.to_ollama_tools([])
        assert schemas == []


class TestOllamaMessageAdapterToOllama:
    def test_system_message(self):
        messages = [LLMMessage(role="system", content="You are helpful")]
        result = OllamaMessageAdapter.to_ollama_messages(messages)
        assert result == [{"role": "system", "content": "You are helpful"}]

    def test_user_message(self):
        messages = [LLMMessage(role="user", content="Hello")]
        result = OllamaMessageAdapter.to_ollama_messages(messages)
        assert result == [{"role": "user", "content": "Hello"}]

    def test_assistant_message_with_content(self):
        messages = [LLMMessage(role="assistant", content="I can help")]
        result = OllamaMessageAdapter.to_ollama_messages(messages)
        assert result == [{"role": "assistant", "content": "I can help"}]

    def test_assistant_message_with_single_tool_call(self):
        messages = [
            LLMMessage(
                role="assistant",
                tool_calls=[ToolCall(id="1", tool_name="get_system_info", arguments={})],
            )
        ]
        result = OllamaMessageAdapter.to_ollama_messages(messages)
        assert len(result) == 1
        assert result[0]["role"] == "assistant"
        assert "content" not in result[0]
        tool_calls = result[0]["tool_calls"]
        assert len(tool_calls) == 1
        assert tool_calls[0]["id"] == "1"
        assert tool_calls[0]["function"]["name"] == "get_system_info"
        assert tool_calls[0]["function"]["arguments"] == "{}"

    def test_assistant_message_with_multiple_tool_calls(self):
        messages = [
            LLMMessage(
                role="assistant",
                tool_calls=[
                    ToolCall(id="1", tool_name="get_cpu_usage", arguments={"target": "server1"}),
                    ToolCall(id="2", tool_name="get_memory_usage", arguments={"target": "server1"}),
                ],
            )
        ]
        result = OllamaMessageAdapter.to_ollama_messages(messages)
        tool_calls = result[0]["tool_calls"]
        assert len(tool_calls) == 2
        names = {tc["function"]["name"] for tc in tool_calls}
        assert "get_cpu_usage" in names
        assert "get_memory_usage" in names

    def test_tool_result_message(self):
        msg = OllamaMessageAdapter.tool_result_to_message("1", "get_system_info", "ok")
        assert msg.role == "tool"
        assert msg.tool_name == "get_system_info"
        assert "get_system_info" in msg.content
        assert "1" in msg.content

    def test_assistant_message_without_content_or_tools(self):
        msg = LLMMessage(role="assistant")
        result = OllamaMessageAdapter.to_ollama_messages([msg])
        assert result == [{"role": "assistant"}]


class TestOllamaMessageAdapterFromOllama:
    def test_text_only_response(self):
        raw = {"message": {"role": "assistant", "content": "Hello world"}}
        result = OllamaMessageAdapter.from_ollama_response(raw)
        assert result.content == "Hello world"
        assert result.tool_calls == []
        assert result.is_final_answer is True

    def test_single_tool_call_response(self):
        import json

        raw = {
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call-1",
                        "function": {
                            "name": "get_system_info",
                            "arguments": json.dumps({"target": "server1"}),
                        },
                    }
                ],
            }
        }
        result = OllamaMessageAdapter.from_ollama_response(raw)
        assert result.content == ""
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].id == "call-1"
        assert result.tool_calls[0].tool_name == "get_system_info"
        assert result.tool_calls[0].arguments == {"target": "server1"}
        assert result.wants_tool_execution is True

    def test_multiple_tool_calls_response(self):
        import json

        raw = {
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "1",
                        "function": {"name": "get_cpu_usage", "arguments": json.dumps({})},
                    },
                    {
                        "id": "2",
                        "function": {"name": "get_memory_usage", "arguments": json.dumps({})},
                    },
                ],
            }
        }
        result = OllamaMessageAdapter.from_ollama_response(raw)
        assert len(result.tool_calls) == 2

    def test_empty_response(self):
        raw = {"message": {"role": "assistant", "content": ""}}
        result = OllamaMessageAdapter.from_ollama_response(raw)
        assert result.content == ""
        assert result.tool_calls == []

    def test_invalid_json_arguments_falls_back(self):
        raw = {
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "1",
                        "function": {"name": "get_info", "arguments": "not-json"},
                    }
                ],
            }
        }
        result = OllamaMessageAdapter.from_ollama_response(raw)
        assert result.tool_calls[0].arguments == {"raw": "not-json"}

    def test_empty_tool_call_arguments(self):
        raw = {
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "1",
                        "function": {"name": "get_info", "arguments": "{}"},
                    }
                ],
            }
        }
        result = OllamaMessageAdapter.from_ollama_response(raw)
        assert result.tool_calls[0].arguments == {}

    def test_none_tool_calls(self):
        raw = {
            "message": {
                "role": "assistant",
                "content": "Hello",
                "tool_calls": None,
            }
        }
        result = OllamaMessageAdapter.from_ollama_response(raw)
        assert result.content == "Hello"
        assert result.tool_calls == []
        assert result.is_final_answer is True
        assert result.wants_tool_execution is False

    def test_thinking_field_and_clean_content(self):
        raw = {
            "message": {
                "role": "assistant",
                "content": "The server is healthy.",
                "thinking": "Let me analyze the request...",
            }
        }
        result = OllamaMessageAdapter.from_ollama_response(raw)
        assert result.content == "The server is healthy."
        assert result.thinking == "Let me analyze the request..."
        assert result.tool_calls == []
        assert result.is_final_answer is True

    def test_thinking_tags_stripped_from_content(self):
        raw = {
            "message": {
                "role": "assistant",
                "content": "<|thinking_start|>analyze<|thinking_end|>The server is healthy.",
            }
        }
        result = OllamaMessageAdapter.from_ollama_response(raw)
        assert "<|thinking" not in result.content
        assert "analyze" not in result.content
        assert "healthy" in result.content

    def test_end_think_tag_stripped_and_keeps_response(self):
        raw = {
            "message": {
                "role": "assistant",
                "content": "Okay, let me think about this.\nTODO\n\nHello! How can I help?",
            }
        }
        result = OllamaMessageAdapter.from_ollama_response(raw)
        assert "TODO" not in result.content
        assert "let me think" not in result.content
        assert "Hello" in result.content
        assert "How can I help" in result.content

    def test_content_without_thinking(self):
        raw = {"message": {"role": "assistant", "content": "Hello world"}}
        result = OllamaMessageAdapter.from_ollama_response(raw)
        assert result.content == "Hello world"
        assert result.thinking == ""
        assert result.tool_calls == []

    def test_tool_call_response_with_thinking(self):
        import json

        raw = {
            "message": {
                "role": "assistant",
                "content": "",
                "thinking": "I need to look up system information.",
                "tool_calls": [
                    {
                        "id": "call-1",
                        "function": {
                            "name": "get_system_info",
                            "arguments": json.dumps({"target": "server1"}),
                        },
                    }
                ],
            }
        }
        result = OllamaMessageAdapter.from_ollama_response(raw)
        assert result.content == ""
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].tool_name == "get_system_info"
        assert result.thinking == "I need to look up system information."
        assert result.wants_tool_execution is True

    def test_final_answer_after_tool_calls(self):
        raw = {
            "message": {
                "role": "assistant",
                "content": "The server is healthy.",
                "thinking": "I have the results.",
            }
        }
        result = OllamaMessageAdapter.from_ollama_response(raw)
        assert result.content == "The server is healthy."
        assert result.is_final_answer is True
        assert result.wants_tool_execution is False
        assert result.thinking == "I have the results."

    def test_empty_tool_calls(self):
        raw = {
            "message": {
                "role": "assistant",
                "content": "Hello",
                "tool_calls": [],
            }
        }
        result = OllamaMessageAdapter.from_ollama_response(raw)
        assert result.content == "Hello"
        assert result.tool_calls == []

    def test_text_only_response_is_final_answer(self):
        raw = {"message": {"role": "assistant", "content": "Hello world"}}
        result = OllamaMessageAdapter.from_ollama_response(raw)
        assert result.content == "Hello world"
        assert result.tool_calls == []
        assert result.is_final_answer is True

    def test_full_conversation_tool_call_then_final_answer(self):
        messages = [
            LLMMessage(role="user", content="Check the server"),
            LLMMessage(
                role="assistant",
                content="",
                tool_calls=[
                    ToolCall(
                        id="call-1",
                        tool_name="get_system_info",
                        arguments={"target": "server1"},
                    )
                ],
            ),
            LLMMessage(
                role="tool",
                tool_name="get_system_info",
                tool_call_id="call-1",
                content="Tool result for get_system_info (call call-1): OK",
            ),
            LLMMessage(role="assistant", content="The server is healthy."),
        ]
        result = OllamaMessageAdapter.to_ollama_messages(messages)
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "assistant"
        assert result[1]["tool_calls"][0]["id"] == "call-1"
        assert result[2]["role"] == "tool"
        assert result[2]["name"] == "get_system_info"
        assert result[2]["tool_call_id"] == "call-1"
        assert result[3]["role"] == "assistant"
        assert result[3]["content"] == "The server is healthy."

    def test_full_conversation_no_tool_calls(self):
        messages = [
            LLMMessage(role="user", content="What is the time?"),
            LLMMessage(role="assistant", content="It is 12:00."),
        ]
        result = OllamaMessageAdapter.to_ollama_messages(messages)
        assert result[0] == {"role": "user", "content": "What is the time?"}
        assert result[1] == {"role": "assistant", "content": "It is 12:00."}


class TestOllamaMessageAdapterToolProtocol:
    def test_tool_result_converts_to_tool_role(self):
        msg = LLMMessage(
            role="tool",
            tool_name="get_system_info",
            content="CPU: 45%",
        )
        result = OllamaMessageAdapter.to_ollama_messages([msg])
        assert len(result) == 1
        assert result[0]["role"] == "tool"
        assert result[0]["name"] == "get_system_info"
        assert result[0]["content"] == "CPU: 45%"
        assert "user" not in [m["role"] for m in result]

    def test_tool_result_without_tool_name_uses_empty_string(self):
        msg = LLMMessage(role="tool", content="some result")
        result = OllamaMessageAdapter.to_ollama_messages([msg])
        assert result[0]["role"] == "tool"
        assert result[0]["name"] == ""
        assert result[0]["content"] == "some result"

    def test_tool_result_is_not_user_role(self):
        msg = LLMMessage(role="tool", tool_name="my_tool", content="result data")
        result = OllamaMessageAdapter.to_ollama_messages([msg])
        assert result[0]["role"] == "tool"
        assert result[0]["name"] == "my_tool"
        for m in result:
            assert m["role"] != "user" or "tool_name" not in m

    def test_full_protocol_single_tool_call(self):
        messages = [
            LLMMessage(role="user", content="Check the server"),
            LLMMessage(
                role="assistant",
                content="",
                tool_calls=[
                    ToolCall(
                        id="call-1",
                        tool_name="get_system_info",
                        arguments={"target": "server1"},
                    )
                ],
            ),
            LLMMessage(
                role="tool",
                tool_name="get_system_info",
                tool_call_id="call-1",
                content="Tool result for get_system_info (call call-1): OK",
            ),
            LLMMessage(role="assistant", content="The server is healthy."),
        ]
        result = OllamaMessageAdapter.to_ollama_messages(messages)

        assert result[0] == {"role": "user", "content": "Check the server"}

        assert result[1]["role"] == "assistant"
        assert "content" not in result[1]
        assert len(result[1]["tool_calls"]) == 1
        assert result[1]["tool_calls"][0]["id"] == "call-1"
        assert result[1]["tool_calls"][0]["function"]["name"] == "get_system_info"
        assert result[1]["tool_calls"][0]["function"]["arguments"] == '{"target": "server1"}'

        assert result[2]["role"] == "tool"
        assert result[2]["name"] == "get_system_info"
        assert result[2]["tool_call_id"] == "call-1"
        assert result[2]["content"] == "Tool result for get_system_info (call call-1): OK"

        assert result[3]["role"] == "assistant"
        assert result[3]["content"] == "The server is healthy."

    def test_full_protocol_multiple_tool_calls(self):
        messages = [
            LLMMessage(role="user", content="Check resources"),
            LLMMessage(
                role="assistant",
                content="",
                tool_calls=[
                    ToolCall(
                        id="1",
                        tool_name="get_cpu_usage",
                        arguments={"target": "server1"},
                    ),
                    ToolCall(
                        id="2",
                        tool_name="get_memory_usage",
                        arguments={"target": "server1"},
                    ),
                ],
            ),
            LLMMessage(
                role="tool",
                tool_name="get_cpu_usage",
                tool_call_id="1",
                content="Tool result for get_cpu_usage (call 1): 45%",
            ),
            LLMMessage(
                role="tool",
                tool_name="get_memory_usage",
                tool_call_id="2",
                content="Tool result for get_memory_usage (call 2): 60%",
            ),
            LLMMessage(
                role="assistant",
                content="CPU at 45%, memory at 60%.",
            ),
        ]
        result = OllamaMessageAdapter.to_ollama_messages(messages)

        assert result[0]["role"] == "user"
        assert result[1]["role"] == "assistant"
        assert len(result[1]["tool_calls"]) == 2
        names = {tc["function"]["name"] for tc in result[1]["tool_calls"]}
        assert "get_cpu_usage" in names
        assert "get_memory_usage" in names

        tool_msgs = [m for m in result if m["role"] == "tool"]
        assert len(tool_msgs) == 2
        tool_names = {m["name"] for m in tool_msgs}
        assert "get_cpu_usage" in tool_names
        assert "get_memory_usage" in tool_names
        for tm in tool_msgs:
            assert "content" in tm
            assert tm["content"].startswith("Tool result for")
            assert "tool_call_id" in tm

        assert result[4]["role"] == "assistant"
        assert result[4]["content"] == "CPU at 45%, memory at 60%."

    def test_assistant_message_with_content_and_tool_calls(self):
        msg = LLMMessage(
            role="assistant",
            content="I need more information",
            tool_calls=[ToolCall(id="a1", tool_name="get_info", arguments={})],
        )
        result = OllamaMessageAdapter.to_ollama_messages([msg])
        assert result[0]["role"] == "assistant"
        assert result[0]["content"] == "I need more information"
        assert len(result[0]["tool_calls"]) == 1
        assert result[0]["tool_calls"][0]["id"] == "a1"

    def test_user_message_never_has_tool_name(self):
        msg = LLMMessage(role="user", content="hello")
        result = OllamaMessageAdapter.to_ollama_messages([msg])
        assert result[0]["role"] == "user"
        assert "tool_name" not in result[0]

    def test_system_message_unaffected(self):
        msg = LLMMessage(role="system", content="Be helpful")
        result = OllamaMessageAdapter.to_ollama_messages([msg])
        assert result[0] == {"role": "system", "content": "Be helpful"}

    def test_conversation_with_denied_tool_continues(self):
        messages = [
            LLMMessage(role="user", content="Investigate"),
            LLMMessage(
                role="assistant",
                content="",
                tool_calls=[ToolCall(id="t1", tool_name="unknown_tool", arguments={})],
            ),
            LLMMessage(
                role="tool",
                tool_name="unknown_tool",
                tool_call_id="t1",
                content="Tool result for unknown_tool (call t1): Denied",
            ),
            LLMMessage(
                role="assistant",
                content="I cannot access that resource.",
            ),
        ]
        result = OllamaMessageAdapter.to_ollama_messages(messages)
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "assistant"
        assert result[2]["role"] == "tool"
        assert result[2]["name"] == "unknown_tool"
        assert result[2]["tool_call_id"] == "t1"
        assert result[3]["role"] == "assistant"
        assert result[3]["content"] == "I cannot access that resource."
