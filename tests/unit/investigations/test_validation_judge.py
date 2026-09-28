import asyncio

import pytest
from packages.agent.llm.contract import LLMResponse
from packages.agent.llm.mock import MockLLMProvider
from packages.investigations.validation_judge import ValidationJudge


def test_validation_judge_parses_structured_judgment():
    llm = MockLLMProvider(
        [
            LLMResponse(
                content=(
                    '{"judgments":[{"action_index":0,"passed":true,'
                    '"summary":"Observed hostname matches the expected condition."}]}'
                )
            )
        ]
    )
    judge = ValidationJudge(llm)

    judgments = asyncio.run(
        judge.judge(
            [
                {
                    "action_tool": "get_system_info",
                    "expected_condition": "Host is reachable",
                    "actual_result": {"hostname": "test-server"},
                }
            ]
        )
    )

    assert judgments.judgments[0].action_index == 0
    assert judgments.judgments[0].passed is True


def test_validation_judge_rejects_invalid_action_index():
    llm = MockLLMProvider(
        [
            LLMResponse(
                content='{"judgments":[{"action_index":1,"passed":true}]}'
            )
        ]
    )
    judge = ValidationJudge(llm)

    with pytest.raises(ValueError, match="invalid action indexes"):
        asyncio.run(
            judge.judge(
                [
                    {
                        "action_tool": "get_system_info",
                        "expected_condition": "Host is reachable",
                        "actual_result": {"hostname": "test-server"},
                    }
                ]
            )
        )


def test_validation_judge_requests_json():
    class CapturingLLM:
        def __init__(self):
            self.request = None

        async def generate(self, request):
            self.request = request
            return LLMResponse(content='{"judgments":[]}')

    llm = CapturingLLM()
    judge = ValidationJudge(llm)

    asyncio.run(
        judge.judge(
            [
                {
                    "action_tool": "get_system_info",
                    "expected_condition": "Host is reachable",
                    "actual_result": {"hostname": "test-server"},
                }
            ]
        )
    )

    assert llm.request.response_format == "json"
    assert llm.request.tools == []
