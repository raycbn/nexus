import json
from uuid import uuid4

import pytest
from apps.api.services import investigation_service
from packages.agent.llm.contract import LLMResponse
from packages.agent.llm.mock import MockLLMProvider
from packages.domain.models.context import TenantContext
from packages.investigations.models import Hypothesis, HypothesisStatus, Investigation
from packages.investigations.validation import ValidationAction
from packages.investigations.validation_executor import ValidationExecutionResult
from packages.tools.registry import ToolRegistry


def test_parse_llm_result_accepts_fenced_json():
    payload = """```json
{"hypotheses":[{"text":"CPU saturation","supporting_tools":["get_cpu_usage"]}],
"validations":[],"finding":"CPU saturation observed","confidence":0.8,
"supporting_tools":["get_cpu_usage"],"uncertainty":null}
```"""
    result = investigation_service.InvestigationApplicationService._parse_llm_result(payload)
    assert result is not None
    assert result.finding == "CPU saturation observed"
    assert result.confidence == 0.8


def test_service_builds_llm_through_ai_router(monkeypatch):
    captured = {}

    class FakeRouter:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    class FakeRoutedProvider:
        def __init__(self, router, task):
            captured["router"] = router
            captured["task"] = task

    monkeypatch.setattr(investigation_service, "AIProviderRouter", FakeRouter)
    monkeypatch.setattr(investigation_service, "RoutedLLMProvider", FakeRoutedProvider)
    service = investigation_service.InvestigationApplicationService(
        TenantContext(
            user_id=uuid4(), organization_id=uuid4(), workspace_id=uuid4(), role="operator"
        ),
        session=object(),
    )
    llm = service._create_llm(ToolRegistry(), "root_cause", num_predict=384)
    assert isinstance(llm, FakeRoutedProvider)
    assert captured["organization_id"] == service.tenant.organization_id
    assert captured["workspace_id"] == service.tenant.workspace_id
    assert captured["num_predict"] == 384
    assert captured["registry"] is not None
    assert captured["task"] == "root_cause"


def test_service_keeps_tenant_context():
    tenant = TenantContext(
        user_id=uuid4(), organization_id=uuid4(), workspace_id=uuid4(), role="operator"
    )
    service = investigation_service.InvestigationApplicationService(tenant)
    assert service.tenant == tenant


@pytest.mark.asyncio
async def test_service_plans_validations_with_infrastructure_tools():
    llm = MockLLMProvider(
        [
            LLMResponse(
                content=(
                    '{"actions":[{"hypothesis_index":0,'
                    '"action_tool":"get_service_status",'
                    '"expected_condition":"Service is healthy"}]}'
                )
            )
        ]
    )
    hypotheses = [Hypothesis(text="The service may be unhealthy")]

    plan = await investigation_service.InvestigationApplicationService._plan_validations(
        llm,
        hypotheses,
    )

    assert len(plan.actions) == 1
    assert plan.actions[0].hypothesis_index == 0
    assert plan.actions[0].action_tool == "get_service_status"


@pytest.mark.asyncio
async def test_service_synthesizes_conclusion_from_validation_state():
    llm = MockLLMProvider(
        [
            LLMResponse(
                content=(
                    '{"finding":"Postgres is unhealthy",'
                    '"confidence":0.9,"uncertainty":null}'
                )
            )
        ]
    )
    investigation = Investigation(
        organization_id=uuid4(), objective="Investigate application health"
    )
    investigation.hypotheses.append(
        Hypothesis(text="Postgres is unhealthy", status=HypothesisStatus.VALIDATED)
    )

    conclusion = await investigation_service.InvestigationApplicationService._synthesize_conclusion(
        llm,
        investigation,
    )

    assert conclusion.finding == "Postgres is unhealthy"
    assert conclusion.confidence == 0.9


@pytest.mark.asyncio
async def test_service_judges_validation_results():
    llm = MockLLMProvider(
        [
            LLMResponse(
                content=(
                    '{"judgments":[{"action_index":0,"passed":false,'
                    '"summary":"Observed value contradicts the expected condition."}]}'
                )
            )
        ]
    )
    result = ValidationExecutionResult(
        action=ValidationAction(
            hypothesis_index=0,
            action_tool="get_system_info",
            expected_condition="Hostname is expected",
        ),
        actual_result={"hostname": "different-host"},
        success=True,
    )

    judgments = await investigation_service.InvestigationApplicationService._judge_validations(
        llm,
        [result],
    )

    assert judgments.judgments[0].passed is False
    assert judgments.judgments[0].summary == (
        "Observed value contradicts the expected condition."
    )


def test_hypothesis_requires_baseline_evidence():
    hypothesis = investigation_service.LLMHypothesisResult(
        text="The API is unhealthy",
        supporting_tools=["get_application_health"],
    )

    assert investigation_service.InvestigationApplicationService._hypothesis_has_evidence(
        hypothesis,
        {"get_application_health": [uuid4()]},
    ) is True
    assert investigation_service.InvestigationApplicationService._hypothesis_has_evidence(
        hypothesis,
        {"get_cpu_usage": [uuid4()]},
    ) is False


def test_parse_llm_result_caps_hypotheses():
    payload = {
        "hypotheses": [
            {
                "text": f"Hypothesis {index}",
                "supporting_tools": ["get_system_info"],
            }
            for index in range(7)
        ],
        "finding": "Several possible findings",
    }

    result = investigation_service.InvestigationApplicationService._parse_llm_result(
        json.dumps(payload)
    )

    assert result is not None
    assert len(result.hypotheses) == 5


def test_parse_llm_result_accepts_hypothesis_only_json():
    payload = """{
      "investigation_id": "nexus-12345",
      "objective": "Investigate the API",
      "hypotheses": [
        {"id": "hypothesis_1", "description": "The API service may be unhealthy."}
      ],
      "validations": []
    }"""
    result = investigation_service.InvestigationApplicationService._parse_llm_result(payload)
    assert result is not None
    assert result.hypotheses[0].text == "The API service may be unhealthy."
    assert result.validations == []
    assert result.confidence == 0.0
    assert result.uncertainty is not None


def test_parse_llm_result_accepts_string_hypotheses_from_ollama():
    payload = """{
      "finding": "Application health is unhealthy",
      "confidence": 0.95,
      "hypotheses": ["PostgreSQL service is down", "Redis service is down"],
      "supporting_tools": ["get_application_health"],
      "uncertainty": "Possible network issues or configuration errors"
    }"""
    result = investigation_service.InvestigationApplicationService._parse_llm_result(payload)
    assert result is not None
    assert [h.text for h in result.hypotheses] == [
        "PostgreSQL service is down",
        "Redis service is down",
    ]
    assert result.finding == "Application health is unhealthy"
    assert result.confidence == 0.95
    assert result.supporting_tools == ["get_application_health"]
    assert result.uncertainty == "Possible network issues or configuration errors"
    assert result.validations == []


def test_parse_llm_result_accepts_qwen_investigation_hypothesis_shape():
    payload = """{
      "investigation": "Application health is unhealthy",
      "hypotheses": [
        {
          "hypothesis": "Postgres service is unhealthy.",
          "evidence": "Application health reports Postgres as unhealthy."
        }
      ]
    }"""
    result = investigation_service.InvestigationApplicationService._parse_llm_result(payload)
    assert result is not None
    assert result.finding == "Application health is unhealthy"
    assert result.hypotheses[0].text == "Postgres service is unhealthy."
    assert result.validations == []
