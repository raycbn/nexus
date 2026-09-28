from uuid import uuid4

from packages.domain.models.agent import Agent
from packages.domain.models.enums import AutonomyLevel, RiskLevel
from packages.domain.models.policy import Policy
from packages.domain.models.remediation import RemediationAction
from packages.policies.remediation import evaluate_remediation


def _action():
    organization_id = uuid4()
    return RemediationAction(
        organization_id=organization_id,
        investigation_id=uuid4(),
        resource_id=uuid4(),
        connector_key="linux",
        action_type="restart_service",
        command_preview="systemctl restart nginx",
        risk_level=RiskLevel.HIGH,
    )


def test_autonomous_low_risk_can_be_allowed_without_approval():
    agent = Agent(
        organization_id=uuid4(), name="a", role="operator", autonomy_level=AutonomyLevel.AUTONOMOUS
    )
    action = RemediationAction(
        organization_id=agent.organization_id,
        investigation_id=uuid4(),
        resource_id=uuid4(),
        connector_key="linux",
        action_type="safe",
        command_preview="echo",
        risk_level=RiskLevel.LOW,
    )
    decision = evaluate_remediation(
        action,
        agent,
        Policy(organization_id=agent.organization_id, name="p", max_risk_level=RiskLevel.LOW),
    )
    assert decision.allowed is True
    assert decision.requires_approval is False


def test_high_risk_autonomy_requires_explicit_policy_flag():
    action = _action()
    agent = Agent(
        organization_id=action.organization_id,
        name="a",
        role="operator",
        autonomy_level=AutonomyLevel.AUTONOMOUS,
    )
    policy = Policy(
        organization_id=action.organization_id,
        name="lab-autonomy",
        max_risk_level=RiskLevel.HIGH,
    )
    decision = evaluate_remediation(action, agent, policy)
    assert decision.execution_mode == "approval"


def test_high_risk_autonomy_is_allowed_only_when_explicitly_enabled():
    action = _action()
    agent = Agent(
        organization_id=action.organization_id,
        name="a",
        role="operator",
        autonomy_level=AutonomyLevel.AUTONOMOUS,
    )
    policy = Policy(
        organization_id=action.organization_id,
        name="lab-autonomy",
        max_risk_level=RiskLevel.HIGH,
        allow_autonomous_high_risk=True,
        allowed_resource_ids=[action.resource_id],
    )
    decision = evaluate_remediation(action, agent, policy)
    assert decision.allowed is True
    assert decision.requires_approval is False
    assert decision.execution_mode == "autonomous"
