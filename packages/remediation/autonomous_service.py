import os
from dataclasses import dataclass

from packages.domain.models.agent import Agent
from packages.domain.models.audit_event import AuditEvent
from packages.domain.models.enums import ActorType, EventType, ResultStatus, RiskLevel
from packages.domain.models.incident import Incident, IncidentStatus
from packages.domain.models.policy import Policy
from packages.domain.models.remediation import RemediationAction, RemediationStatus
from packages.domain.models.resource import Resource
from packages.persistence.repositories.audit import AuditEventRepository
from packages.persistence.repositories.incident import IncidentPostgresRepository
from packages.persistence.repositories.remediation import RemediationActionRepository
from packages.persistence.repositories.remediation_attempt import RemediationAttemptRepository
from packages.remediation.action_specs import build_write_action
from packages.remediation.autonomous_loop import (
    AutonomousLoopResult,
    evaluate_autonomous_loop,
    run_autonomous_loop,
)
from packages.remediation.executor import RemediationExecutor
from packages.remediation.idempotency import remediation_fingerprint
from packages.remediation.safety import check_kill_switch
from packages.remediation.verifier import RestartServiceVerifier


@dataclass(frozen=True)
class AutonomousRemediationResult:
    action: RemediationAction
    loop: AutonomousLoopResult
    incident_resolved: bool = False


def _service_name(action: RemediationAction) -> str:
    return action.command_preview.rsplit(" ", 1)[-1]


def _connector_action(action: RemediationAction):
    return build_write_action(action.action_type, {"service": _service_name(action)})


async def _read_service_status(connector, resource: Resource, service: str) -> str:
    result = await connector.execute_read(resource, f"sudo systemctl is-active -- {service}")
    if result.success and result.data:
        status = result.data.strip().splitlines()[0]
        if status in {"active", "running", "inactive", "failed"}:
            return status

    fallback = await connector.execute_read(resource, f"service {service} status")
    if fallback.success:
        return "active"
    if service == "nginx":
        process = await connector.execute_read(resource, "pgrep -x nginx")
        if process.success and process.data:
            return "active"
    return "unknown"


async def execute_autonomous_remediation(
    action: RemediationAction,
    agent: Agent,
    resource: Resource,
    connector,
    incident: Incident,
    session,
    *,
    max_retries: int = 0,
    dry_run: bool = False,
    policy_override: Policy | None = None,
) -> AutonomousRemediationResult:
    repository = RemediationActionRepository(session)
    attempts_repo = RemediationAttemptRepository(session)
    audit = AuditEventRepository(session)
    policy = policy_override or Policy(
        organization_id=action.organization_id,
        name="runtime-autonomous-lab",
        max_risk_level=RiskLevel.HIGH,
        allow_autonomous_high_risk=os.getenv("NEXUS_AUTONOMOUS_HIGH_RISK", "false").lower()
        == "true",
        allowed_resource_ids=[resource.id],
    )
    decision = evaluate_autonomous_loop(action, agent, policy)
    await audit.create(
        AuditEvent(
            organization_id=action.organization_id,
            workspace_id=action.workspace_id,
            actor_type=ActorType.AGENT,
            actor_id=agent.id,
            event_type=EventType.POLICY_CHECKED,
            resource_id=resource.id,
            action="remediation.autonomous_decision",
            result_status=ResultStatus.SUCCESS
            if decision.decision == "autonomous"
            else ResultStatus.DENIED,
            metadata={
                "action_id": str(action.id),
                "agent_id": str(agent.id),
                "decision": decision.decision,
                "reason": decision.reason,
            },
        ),
        incident_id=incident.id,
    )
    await session.commit()
    if decision.decision != "autonomous":
        return AutonomousRemediationResult(action, decision, False)
    if dry_run:
        await connector.connect(resource)
        try:
            verifier = RestartServiceVerifier(
                lambda name: _read_service_status(connector, resource, name)
            )
            loop = await run_autonomous_loop(
                action,
                agent,
                policy,
                resource,
                _connector_action(action),
                RemediationExecutor(connector),
                verifier,
                max_retries=max_retries,
                dry_run=True,
            )
        finally:
            await connector.disconnect(resource)
        simulated = AutonomousLoopResult(
            action.id,
            "simulated",
            loop.requires_approval,
            loop.reason or "Autonomous remediation dry-run completed",
            loop.execution,
            loop.verification,
            loop.attempts,
            loop.evidence,
        )
        return AutonomousRemediationResult(action, simulated, False)
    claimed = await repository.claim_for_autonomous(
        action.id, action.organization_id, action.workspace_id
    )
    if claimed is None:
        return AutonomousRemediationResult(
            action,
            AutonomousLoopResult(action.id, "busy", False, "Remediation is already executing"),
            False,
        )
    action = claimed
    await session.commit()

    async def record_attempt(number, status, message, evidence):
        evidence = {**evidence, "pre_state": pre_state} if pre_state is not None else evidence
        await attempts_repo.create(
            action.id,
            action.organization_id,
            action.workspace_id,
            number,
            status,
            message,
            evidence,
        )
        await audit.create(
            AuditEvent(
                organization_id=action.organization_id,
                workspace_id=action.workspace_id,
                actor_type=ActorType.AGENT,
                actor_id=agent.id,
                event_type=EventType.TOOL_INVOKED,
                resource_id=resource.id,
                action="remediation.attempt",
                result_status=ResultStatus.SUCCESS
                if status == "verified"
                else ResultStatus.FAILURE,
                metadata={
                "action_id": str(action.id),
                "attempt": number,
                "status": status,
                "fingerprint": remediation_fingerprint(action),
            },
            ),
            incident_id=incident.id,
        )
        await session.commit()

    preflight = autonomous_preflight(connector, resource, dry_run=dry_run)
    if not preflight.allowed:
        return AutonomousRemediationResult(
            action,
            AutonomousLoopResult(action.id, "blocked", False, preflight.reason),
            False,
        )
    await connector.connect(resource)
    try:
        pre_state = None
        if hasattr(connector, "execute_read"):
            pre_state = await _read_service_status(
                connector, resource, _service_name(action)
            )
        verifier = RestartServiceVerifier(
            lambda name: _read_service_status(connector, resource, name)
        )
        loop = await run_autonomous_loop(
            action,
            agent,
            policy,
            resource,
            _connector_action(action),
            RemediationExecutor(connector),
            verifier,
            max_retries=max_retries,
            attempt_recorder=record_attempt,
        )
    finally:
        await connector.disconnect(resource)

    verified = bool(loop.verification and loop.verification.verified)
    if verified:
        await repository.update_status(
            action.id, action.organization_id, RemediationStatus.EXECUTED, action.workspace_id
        )
        final_status = RemediationStatus.VERIFIED
    else:
        final_status = RemediationStatus.FAILED
    updated = await repository.update_status(
        action.id, action.organization_id, final_status, action.workspace_id
    )
    incident_resolved = False
    if verified:
        incident_repo = IncidentPostgresRepository(session)
        current_incident = await incident_repo.get(
            incident.id, action.organization_id, action.workspace_id
        )
        if current_incident is not None:
            incident_resolved = current_incident.transition_status(
                IncidentStatus.RESOLVED, actor_type="agent", actor_id=agent.id
            )
            if incident_resolved:
                await incident_repo.update(
                    current_incident, action.organization_id, action.workspace_id
                )
    await audit.create(
        AuditEvent(
            organization_id=action.organization_id,
            workspace_id=action.workspace_id,
            actor_type=ActorType.AGENT,
            actor_id=agent.id,
            event_type=EventType.INCIDENT_RESOLVED if incident_resolved else EventType.TOOL_INVOKED,
            resource_id=resource.id,
            action="remediation.loop_completed",
            result_status=ResultStatus.SUCCESS if verified else ResultStatus.FAILURE,
            metadata={
                "action_id": str(action.id),
                "attempts": loop.attempts,
                "decision": loop.decision,
                "incident_resolved": incident_resolved,
            },
        ),
        incident_id=incident.id,
    )
    await session.commit()
    return AutonomousRemediationResult(updated, loop, incident_resolved)

@dataclass(frozen=True)
class AutonomousPreflight:
    allowed: bool
    reason: str


def autonomous_preflight(connector, resource, *, dry_run: bool) -> AutonomousPreflight:
    if dry_run:
        return AutonomousPreflight(True, "Dry-run does not require connector writes")
    if resource.environment != "lab":
        return AutonomousPreflight(False, "Autonomous writes require a lab resource")
    safety = check_kill_switch()
    if not safety.allowed:
        return AutonomousPreflight(False, safety.reason or "Kill switch blocks execution")
    if not connector.capabilities.write:
        return AutonomousPreflight(False, "Connector write capability is disabled")
    return AutonomousPreflight(True, "Autonomous write preflight passed")
