from uuid import uuid4

import pytest
from packages.domain.models.enums import RiskLevel
from packages.investigations.models import (
    Conclusion,
    Evidence,
    Hypothesis,
    HypothesisStatus,
    Investigation,
    Validation,
)
from packages.remediation.auto_proposer import (
    AutoProposalError,
    select_validated_restart_action,
)


def make_investigation(confidence=1.0, validated=True, passed=True):
    resource_id = uuid4()
    investigation = Investigation(
        organization_id=uuid4(), workspace_id=uuid4(), objective="nginx failure"
    )
    investigation.evidence.append(
        Evidence(
            source_tool="get_service_status",
            resource_id=resource_id,
            observed_value={"service": "nginx", "status": "inactive"},
        )
    )
    investigation.hypotheses.append(
        Hypothesis(
            text="nginx is stopped",
            status=HypothesisStatus.VALIDATED if validated else HypothesisStatus.PROPOSED,
        )
    )
    investigation.validations.append(
        Validation(
            action_tool="get_service_status",
            expected_condition="service active",
            passed=passed,
        )
    )
    investigation.set_conclusion(
        Conclusion(finding="nginx is stopped", confidence=confidence)
    )
    return investigation, resource_id


def test_auto_proposer_builds_structured_restart_action():
    investigation, resource_id = make_investigation()
    action = select_validated_restart_action(investigation)
    assert action.action_type == "restart_service"
    assert action.resource_id == resource_id
    assert action.risk_level == RiskLevel.HIGH
    assert action.requires_approval is True
    assert action.dry_run is True


@pytest.mark.parametrize(
    "confidence,validated,passed",
    [(0.79, True, True), (1.0, False, True), (1.0, True, False)],
)
def test_auto_proposer_refuses_unsafe_evidence(confidence, validated, passed):
    investigation, _ = make_investigation(confidence, validated, passed)
    with pytest.raises(AutoProposalError):
        select_validated_restart_action(investigation)
