import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from packages.connectors.base.models import WriteAction
from packages.domain.models.agent import Agent
from packages.domain.models.policy import Policy
from packages.domain.models.remediation import RemediationAction
from packages.domain.models.resource import Resource
from packages.remediation.autonomous import can_auto_execute, plan_autonomous_remediation
from packages.remediation.executor import ExecutionOutcome, RemediationExecutor
from packages.remediation.retry_policy import RetryPolicy
from packages.remediation.verifier import RemediationVerifier, VerificationResult

AttemptRecorder = Callable[[int, str, str | None, dict[str, Any]], Awaitable[None]]


@dataclass(frozen=True)
class AutonomousLoopResult:
    action_id: UUID
    decision: str
    requires_approval: bool
    reason: str | None
    execution: ExecutionOutcome | None = None
    verification: VerificationResult | None = None
    attempts: int = 0
    evidence: dict[str, Any] = field(default_factory=dict)


def evaluate_autonomous_loop(
    action: RemediationAction, agent: Agent, policy: Policy | None
) -> AutonomousLoopResult:
    plan = plan_autonomous_remediation(action, agent, policy)
    decision = "autonomous" if can_auto_execute(plan) else plan.execution_mode
    return AutonomousLoopResult(action.id, decision, plan.requires_approval, plan.reason)


async def run_autonomous_loop(
    action: RemediationAction,
    agent: Agent,
    policy: Policy | None,
    resource: Resource,
    connector_action: WriteAction,
    executor: RemediationExecutor,
    verifier: RemediationVerifier,
    *,
    max_retries: int = 0,
    dry_run: bool = False,
    attempt_recorder: AttemptRecorder | None = None,
    retry_policy: RetryPolicy | None = None,
) -> AutonomousLoopResult:
    if max_retries < 0:
        raise ValueError("max_retries must be non-negative")
    plan = plan_autonomous_remediation(action, agent, policy)
    if not can_auto_execute(plan):
        return AutonomousLoopResult(
            action.id, plan.execution_mode, plan.requires_approval, plan.reason
        )
    retry_config = retry_policy or RetryPolicy(max_attempts=max_retries + 1)
    attempts = 0
    last_execution = None
    last_verification = None
    for _ in range(retry_config.max_attempts):
        attempts += 1
        last_execution = await executor.run(
            action,
            resource,
            connector_action,
            dry_run=dry_run,
            autonomous_authorized=True,
        )
        if not last_execution.accepted:
            if attempt_recorder:
                await attempt_recorder(attempts, "execution_failed", last_execution.message, {})
            if attempts < retry_config.max_attempts:
                await asyncio.sleep(retry_config.delay_for_retry(attempts))
                continue
            return AutonomousLoopResult(
                action.id, "failed", False, last_execution.message,
                last_execution, None, attempts,
            )
        last_verification = await verifier.verify(action)
        if last_verification.verified:
            if attempt_recorder:
                await attempt_recorder(
                    attempts, "verified", last_verification.message, last_verification.evidence
                )
            return AutonomousLoopResult(
                action.id, "verified", False, last_verification.message,
                last_execution, last_verification, attempts, last_verification.evidence,
            )
        if attempt_recorder:
            await attempt_recorder(
                attempts, "verification_failed", last_verification.message,
                last_verification.evidence,
            )
        if attempts < retry_config.max_attempts:
            await asyncio.sleep(retry_config.delay_for_retry(attempts))
    return AutonomousLoopResult(
        action.id, "failed", False,
        last_verification.message if last_verification else "Verification failed",
        last_execution, last_verification, attempts,
        last_verification.evidence if last_verification else {},
    )
