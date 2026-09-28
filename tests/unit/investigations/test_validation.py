import pytest
from packages.investigations.validation import ValidationAction, ValidationPlan
from pydantic import ValidationError


def test_validation_plan_contains_hypothesis_actions():
    plan = ValidationPlan(
        actions=[
            ValidationAction(
                hypothesis_index=0,
                action_tool="get_service_status",
                expected_condition="PostgreSQL service reports healthy",
            )
        ]
    )

    assert len(plan.actions) == 1
    assert plan.actions[0].hypothesis_index == 0
    assert plan.actions[0].action_tool == "get_service_status"


def test_validation_plan_defaults_to_no_actions():
    plan = ValidationPlan()

    assert plan.actions == []


def test_validation_action_rejects_empty_tool_or_condition():
    with pytest.raises(ValidationError):
        ValidationAction(
            hypothesis_index=0,
            action_tool="",
            expected_condition="Service is healthy",
        )

    with pytest.raises(ValidationError):
        ValidationAction(
            hypothesis_index=0,
            action_tool="get_service_status",
            expected_condition="",
        )
