from uuid import uuid4

from packages.domain.models.agent import Agent
from packages.domain.models.enums import AutonomyLevel, RiskLevel
from packages.domain.models.policy import Policy
from packages.domain.models.remediation import RemediationAction
from packages.policies.remediation import evaluate_remediation


def _action():
    return RemediationAction(
        organization_id=uuid4(),
        workspace_id=None,
        investigation_id=uuid4(),
        resource_id=uuid4(),
        connector_key="linux",
        action_type="restart_service",
        command_preview="systemctl restart nginx",
        risk_level=RiskLevel.HIGH,
    )


def test_read_only_agent_cannot_remediate():
    agent = Agent(
        organization_id=uuid4(),
        name="a",
        role="investigator",
        autonomy_level=AutonomyLevel.READ_ONLY,
    )
    decision = evaluate_remediation(_action(), agent, None)
    assert decision.allowed is False


def test_approval_agent_requires_approval():
    agent = Agent(
        organization_id=uuid4(),
        name="a",
        role="operator",
        autonomy_level=AutonomyLevel.APPROVAL_REQUIRED,
    )
    decision = evaluate_remediation(_action(), agent, None)
    assert decision.allowed is True
    assert decision.requires_approval is True


def test_policy_max_risk_can_deny():
    action = _action()
    agent = Agent(
        organization_id=uuid4(), name="a", role="operator", autonomy_level=AutonomyLevel.AUTONOMOUS
    )
    policy = Policy(
        organization_id=agent.organization_id, name="safe", max_risk_level=RiskLevel.MEDIUM
    )
    decision = evaluate_remediation(action, agent, policy)
    assert decision.allowed is False
