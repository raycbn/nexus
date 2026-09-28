from dataclasses import dataclass

from packages.domain.models.agent import Agent
from packages.domain.models.policy import Policy
from packages.domain.models.remediation import RemediationAction
from packages.policies.remediation import evaluate_remediation


@dataclass(frozen=True)
class AutonomousPlan:
    allowed: bool
    execution_mode: str
    requires_approval: bool
    reason: str | None = None


def plan_autonomous_remediation(
    action: RemediationAction, agent: Agent, policy: Policy | None
) -> AutonomousPlan:
    decision = evaluate_remediation(action, agent, policy)
    return AutonomousPlan(
        allowed=decision.allowed,
        execution_mode=decision.execution_mode,
        requires_approval=decision.requires_approval,
        reason=decision.reason,
    )


def can_auto_execute(plan: AutonomousPlan) -> bool:
    return plan.allowed and plan.execution_mode == "autonomous" and not plan.requires_approval
