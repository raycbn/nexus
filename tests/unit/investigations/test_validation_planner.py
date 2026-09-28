import pytest
from packages.agent.llm.contract import LLMResponse
from packages.agent.llm.mock import MockLLMProvider
from packages.investigations.models import Hypothesis
from packages.investigations.validation_planner import ValidationPlanner


@pytest.mark.asyncio
async def test_validation_planner_builds_plan_from_llm_response():
    llm = MockLLMProvider(
        [
            LLMResponse(
                content=(
                    '{"actions":[{"hypothesis_index":0,"action_tool":"get_service_status",'
                    '"expected_condition":"PostgreSQL is healthy"}]}'
                )
            )
        ]
    )
    planner = ValidationPlanner(llm, ["get_service_status", "get_application_health"])
    hypotheses = [Hypothesis(text="PostgreSQL is unhealthy")]

    plan = await planner.plan(hypotheses)

    assert len(plan.actions) == 1
    assert plan.actions[0].hypothesis_index == 0
    assert plan.actions[0].action_tool == "get_service_status"
    assert llm.call_count == 1


@pytest.mark.asyncio
async def test_validation_planner_requests_json_and_lists_available_tools():
    llm = MockLLMProvider([LLMResponse(content='{"actions":[]}')])
    planner = ValidationPlanner(llm, ["get_service_status", "get_application_health"])

    await planner.plan([Hypothesis(text="The service is unhealthy")])

    request = llm.call_log[0]
    assert request.response_format == "json"
    assert "get_service_status" in request.messages[1].content
    assert "get_application_health" in request.messages[1].content


def test_validation_planner_rejects_invalid_json():
    llm = MockLLMProvider([])
    planner = ValidationPlanner(llm, [])

    with pytest.raises(ValueError, match="invalid JSON"):
        planner._parse_response(LLMResponse(content="not-json"))


@pytest.mark.asyncio
async def test_validation_planner_rejects_unavailable_tools():
    llm = MockLLMProvider(
        [
            LLMResponse(
                content=(
                    '{"actions":[{"hypothesis_index":0,"action_tool":"restart_service",'
                    '"expected_condition":"Service is healthy"}]}'
                )
            )
        ]
    )
    planner = ValidationPlanner(llm, ["get_service_status"])

    with pytest.raises(ValueError, match="unavailable tools"):
        await planner.plan([Hypothesis(text="The service is unhealthy")])


@pytest.mark.asyncio
async def test_validation_planner_rejects_invalid_hypothesis_index():
    llm = MockLLMProvider(
        [
            LLMResponse(
                content=(
                    '{"actions":[{"hypothesis_index":1,"action_tool":"get_service_status",'
                    '"expected_condition":"Service is healthy"}]}'
                )
            )
        ]
    )
    planner = ValidationPlanner(llm, ["get_service_status"])

    with pytest.raises(ValueError, match="invalid hypothesis indexes"):
        await planner.plan([Hypothesis(text="The service is unhealthy")])


@pytest.mark.asyncio
async def test_validation_planner_rejects_too_many_actions():
    actions = ",".join(
        (
            '{"hypothesis_index":0,"action_tool":"get_service_status",'
            '"expected_condition":"Service is healthy"}'
        )
        for _ in range(9)
    )
    llm = MockLLMProvider(
        [LLMResponse(content=f'{{"actions":[{actions}]}}')]
    )
    planner = ValidationPlanner(llm, ["get_service_status"])

    with pytest.raises(ValueError, match="too many actions"):
        await planner.plan([Hypothesis(text="The service is unhealthy")])
