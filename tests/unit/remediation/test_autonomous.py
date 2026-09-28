from uuid import uuid4

from packages.domain.models.agent import Agent
from packages.domain.models.enums import AutonomyLevel, RiskLevel
from packages.domain.models.policy import Policy
from packages.domain.models.remediation import RemediationAction
from packages.remediation.autonomous import can_auto_execute, plan_autonomous_remediation


def make_action(risk=RiskLevel.LOW):
    return RemediationAction(
        organization_id=uuid4(),
        workspace_id=uuid4(),
        investigation_id=uuid4(),
        resource_id=uuid4(),
        connector_key="linux",
        action_type="restart_service",
        command_preview="systemctl restart nginx",
        risk_level=risk,
        requires_approval=False,
        dry_run=False,
    )


def make_agent(org):
    return Agent(
        organization_id=org,
        name="autonomous",
        role="remediator",
        autonomy_level=AutonomyLevel.AUTONOMOUS,
    )


def test_autonomous_low_risk_is_allowed():
    action = make_action()
    agent = make_agent(action.organization_id)
    policy = Policy(
        organization_id=action.organization_id, name="safe", max_risk_level=RiskLevel.LOW
    )
    plan = plan_autonomous_remediation(action, agent, policy)
    assert plan.execution_mode == "autonomous"
    assert can_auto_execute(plan)


def test_high_risk_still_requires_approval():
    action = make_action(RiskLevel.HIGH)
    agent = make_agent(action.organization_id)
    policy = Policy(
        organization_id=action.organization_id, name="safe", max_risk_level=RiskLevel.HIGH
    )
    plan = plan_autonomous_remediation(action, agent, policy)
    assert plan.execution_mode == "approval"
    assert not can_auto_execute(plan)


def test_approval_required_agent_never_auto_executes():
    action = make_action()
    agent = Agent(
        organization_id=action.organization_id,
        name="guarded",
        role="remediator",
        autonomy_level=AutonomyLevel.APPROVAL_REQUIRED,
    )
    plan = plan_autonomous_remediation(action, agent, None)
    assert plan.requires_approval
    assert not can_auto_execute(plan)
