from dataclasses import dataclass

from packages.domain.models.agent import Agent
from packages.domain.models.enums import AutonomyLevel, RiskLevel
from packages.domain.models.policy import Policy
from packages.domain.models.remediation import RemediationAction


@dataclass(frozen=True)
class RemediationDecision:
    allowed: bool
    requires_approval: bool
    reason: str | None = None
    execution_mode: str = "approval"


_RISK_ORDER = {
    RiskLevel.LOW: 0,
    RiskLevel.MEDIUM: 1,
    RiskLevel.HIGH: 2,
    RiskLevel.CRITICAL: 3,
}


def evaluate_remediation(
    action: RemediationAction, agent: Agent, policy: Policy | None
) -> RemediationDecision:
    if agent.autonomy_level == AutonomyLevel.READ_ONLY:
        return RemediationDecision(False, True, "Agent autonomy is read-only", "blocked")
    if policy is not None and _RISK_ORDER[action.risk_level] > _RISK_ORDER[policy.max_risk_level]:
        return RemediationDecision(False, True, "Risk level exceeds policy maximum", "blocked")
    if action.resource_id not in _allowed_resources(action, policy):
        return RemediationDecision(False, True, "Resource is not allowed by policy", "blocked")
    if policy is not None and action.action_type in policy.denied_tool_ids:
        return RemediationDecision(False, True, "Action is denied by policy", "blocked")
    if policy is not None and action.action_type in policy.approval_required_tool_ids:
        return RemediationDecision(True, True, "Action requires policy approval", "approval")
    if agent.autonomy_level == AutonomyLevel.APPROVAL_REQUIRED:
        return RemediationDecision(True, True, execution_mode="approval")
    if action.risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
        if (
            policy is not None
            and policy.allow_autonomous_high_risk
            and agent.autonomy_level == AutonomyLevel.AUTONOMOUS
        ):
            return RemediationDecision(
                True,
                False,
                "Policy explicitly permits autonomous high-risk remediation",
                "autonomous",
            )
        return RemediationDecision(
            True, True, "High-risk actions require explicit approval", "approval"
        )
    if agent.autonomy_level == AutonomyLevel.AUTONOMOUS:
        return RemediationDecision(
            True, False, "Policy-authorized autonomous remediation", "autonomous"
        )
    return RemediationDecision(True, False, execution_mode="approval")


def _allowed_resources(action: RemediationAction, policy: Policy | None) -> set:
    if policy is None or not policy.allowed_resource_ids:
        return {action.resource_id}
    return set(policy.allowed_resource_ids)
