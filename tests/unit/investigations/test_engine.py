from uuid import uuid4

import pytest
from packages.domain.models.agent import Agent
from packages.domain.models.enums import ResourceType
from packages.domain.models.resource import Resource
from packages.domain.resource_graph import ResourceGraph
from packages.investigations.engine import InvestigationEngine
from packages.investigations.models import Evidence, HypothesisStatus
from packages.investigations.validation import ValidationAction
from packages.investigations.validation_executor import ValidationExecutionResult


def make_engine():
    organization_id = uuid4()
    agent = Agent(
        organization_id=organization_id,
        workspace_id=uuid4(),
        name="Investigator",
        role="investigator",
        autonomy_level="read_only",
        allowed_tool_ids=[],
    )
    return InvestigationEngine(
        runtime=None,
        agent=agent,
        allowed_tool_identifiers=["get_system_info"],
        organization_id=organization_id,
        workspace_id=agent.workspace_id,
    )


def test_engine_hypothesis_key_normalizes_whitespace_and_case():
    assert InvestigationEngine._hypothesis_key("  API   Unhealthy ") == "api unhealthy"


def test_engine_deduplicates_hypotheses():
    engine = make_engine()

    first = engine.form_hypothesis("The API is unhealthy")
    duplicate = engine.form_hypothesis("  the   api is   unhealthy. ")

    assert first is not None
    assert duplicate is None
    assert len(engine.investigation.hypotheses) == 1


def test_engine_deduplicates_semantically_similar_hypotheses():
    engine = make_engine()

    first = engine.form_hypothesis("API unhealthy due to memory pressure")
    duplicate = engine.form_hypothesis("The API is unhealthy because of memory pressure")

    assert first is not None
    assert duplicate is None


def test_engine_keeps_distinct_hypotheses():
    engine = make_engine()

    first = engine.form_hypothesis("API unhealthy due to memory pressure")
    second = engine.form_hypothesis("Database connection pool is exhausted")

    assert first is not None
    assert second is not None
    assert len(engine.investigation.hypotheses) == 2


def test_engine_applies_validation_results_to_hypotheses():
    engine = make_engine()
    hypothesis = engine.form_hypothesis("The host is reachable")
    action = ValidationAction(
        hypothesis_index=0,
        action_tool="get_system_info",
        expected_condition="Host is reachable",
    )
    result = ValidationExecutionResult(
        action=action,
        actual_result={"hostname": "test-server"},
        success=True,
    )

    engine.apply_validation_results([result])

    assert engine.investigation.validations[0].action_tool == "get_system_info"
    assert engine.investigation.validations[0].actual_result == {"hostname": "test-server"}
    assert hypothesis.status == HypothesisStatus.SUPPORTED


def test_engine_marks_failed_validation_as_contradicted():
    engine = make_engine()
    hypothesis = engine.form_hypothesis("The host has the expected hostname")
    action = ValidationAction(
        hypothesis_index=0,
        action_tool="get_system_info",
        expected_condition="Hostname is expected",
    )
    result = ValidationExecutionResult(
        action=action,
        actual_result={"hostname": "different-host"},
        success=True,
    )
    result.passed = False

    engine.apply_validation_results([result])

    assert engine.investigation.validations[0].passed is False
    evidence_id = engine.investigation.validations[0].evidence_ids[0]
    assert evidence_id in hypothesis.contradicting_evidence_ids
    assert hypothesis.status == HypothesisStatus.CONTRADICTED


def test_engine_calculates_confidence_from_validation_states():
    engine = make_engine()
    first = engine.form_hypothesis("First")
    second = engine.form_hypothesis("Second")
    first.status = HypothesisStatus.VALIDATED
    second.status = HypothesisStatus.CONTRADICTED

    assert engine.calculate_confidence() == 0.38


def test_engine_resolves_evidence_resource_lineage():
    engine = make_engine()
    host = Resource(
        organization_id=engine.investigation.organization_id,
        name="linux-lab-01",
        resource_type=ResourceType.LINUX_SERVER,
    )
    service = Resource(
        organization_id=engine.investigation.organization_id,
        name="nginx",
        resource_type=ResourceType.SERVICE,
        parent_resource_id=host.id,
    )
    evidence = Evidence(source_tool="get_service_status", resource_id=service.id)
    engine.investigation.add_evidence(evidence)

    graph = ResourceGraph([host, service])

    assert engine.evidence_resource_lineage(graph) == {
        evidence.id: [service.id, host.id]
    }


def test_engine_confidence_is_zero_without_hypotheses():
    engine = make_engine()

    assert engine.calculate_confidence() == 0.0


def test_engine_rejects_unknown_validation_hypothesis():
    engine = make_engine()
    action = ValidationAction(
        hypothesis_index=2,
        action_tool="get_system_info",
        expected_condition="Host is reachable",
    )
    result = ValidationExecutionResult(
        action=action,
        actual_result={"hostname": "test-server"},
        success=True,
    )

    with pytest.raises(ValueError, match="unknown hypothesis"):
        engine.apply_validation_results([result])
