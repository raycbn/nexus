import asyncio
from uuid import uuid4

import pytest
from packages.domain.models.policy import Policy as PolicyModel
from packages.investigations.validation import ValidationAction, ValidationPlan
from packages.investigations.validation_executor import ValidationExecutor
from packages.investigations.validation_judge import ValidationJudgment, ValidationJudgments
from packages.policies.evaluator import PolicyEvaluator
from packages.tools.providers.mock_tools import GetSystemInfoTool
from packages.tools.registry import ToolRegistry


def make_executor(allowed=None):
    registry = ToolRegistry()
    registry.register(GetSystemInfoTool())
    policy = PolicyModel(
        organization_id=uuid4(),
        name="validation-test",
        allowed_tool_ids=allowed if allowed is not None else ["get_system_info"],
    )
    return ValidationExecutor(
        registry,
        PolicyEvaluator(policy),
        allowed if allowed is not None else ["get_system_info"],
    )


def test_executor_runs_allowed_read_only_action():
    executor = make_executor()
    plan = ValidationPlan(
        actions=[
            ValidationAction(
                hypothesis_index=0,
                action_tool="get_system_info",
                expected_condition="Host is reachable",
            )
        ]
    )

    results = asyncio.run(executor.execute(plan))

    assert len(results) == 1
    assert results[0].success is True
    assert results[0].actual_result["hostname"] == "test-server"


def test_executor_applies_judgments_to_results():
    executor = make_executor()
    plan = ValidationPlan(
        actions=[
            ValidationAction(
                hypothesis_index=0,
                action_tool="get_system_info",
                expected_condition="Host is reachable",
            ),
            ValidationAction(
                hypothesis_index=1,
                action_tool="get_system_info",
                expected_condition="Hostname is expected",
            ),
        ]
    )

    results = asyncio.run(executor.execute(plan))
    judgments = ValidationJudgments(
        judgments=[
            ValidationJudgment(action_index=0, passed=True, summary="Reachable"),
            ValidationJudgment(action_index=1, passed=False, summary="Hostname differs"),
        ]
    )

    executor.apply_judgments(results, judgments)

    assert results[0].passed is True
    assert results[0].summary == "Reachable"
    assert results[1].passed is False
    assert results[1].summary == "Hostname differs"


def test_executor_rejects_incomplete_judgments():
    executor = make_executor()
    plan = ValidationPlan(
        actions=[
            ValidationAction(
                hypothesis_index=0,
                action_tool="get_system_info",
                expected_condition="Host is reachable",
            ),
            ValidationAction(
                hypothesis_index=1,
                action_tool="get_system_info",
                expected_condition="Hostname is expected",
            ),
        ]
    )

    results = asyncio.run(executor.execute(plan))
    judgments = ValidationJudgments(
        judgments=[ValidationJudgment(action_index=0, passed=True)]
    )

    with pytest.raises(ValueError, match="omitted action indexes"):
        executor.apply_judgments(results, judgments)


def test_executor_rejects_duplicate_judgments():
    executor = make_executor()
    plan = ValidationPlan(
        actions=[
            ValidationAction(
                hypothesis_index=0,
                action_tool="get_system_info",
                expected_condition="Host is reachable",
            )
        ]
    )

    results = asyncio.run(executor.execute(plan))
    judgments = ValidationJudgments(
        judgments=[
            ValidationJudgment(action_index=0, passed=True),
            ValidationJudgment(action_index=0, passed=False),
        ]
    )

    with pytest.raises(ValueError, match="duplicate action index"):
        executor.apply_judgments(results, judgments)


def test_executor_rejects_denied_action():
    executor = make_executor(allowed=[])
    plan = ValidationPlan(
        actions=[
            ValidationAction(
                hypothesis_index=0,
                action_tool="get_system_info",
                expected_condition="Host is reachable",
            )
        ]
    )

    with pytest.raises(ValueError, match="denied"):
        asyncio.run(executor.execute(plan))
