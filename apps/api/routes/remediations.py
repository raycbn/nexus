from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from packages.auth import get_current_principal, get_tenant_context, require_permissions
from packages.domain.models.audit_event import AuditEvent
from packages.domain.models.context import TenantContext
from packages.domain.models.enums import ActorType, EventType, ResultStatus
from packages.domain.models.remediation import RemediationStatus
from packages.persistence.repositories.audit import AuditEventRepository
from packages.persistence.repositories.core import CoreRepository
from packages.persistence.repositories.incident import IncidentPostgresRepository
from packages.persistence.repositories.investigation import InvestigationPostgresRepository
from packages.persistence.repositories.remediation import RemediationActionRepository
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db_session

router = APIRouter(prefix="/remediations", tags=["remediations"])
TenantContextDep = Annotated[TenantContext, Depends(get_tenant_context)]


class RemediationProposalCreateDTO(BaseModel):
    investigation_id: UUID
    resource_id: UUID
    service: str = Field(min_length=1, max_length=128)


class AutomaticRemediationProposalDTO(BaseModel):
    action_id: UUID
    investigation_id: UUID
    resource_id: UUID
    action_type: str
    service: str
    risk_level: str
    requires_approval: bool


class RemediationSimulationDTO(BaseModel):
    action_id: UUID
    accepted: bool
    simulated: bool
    message: str


class AutonomousRemediationRequestDTO(BaseModel):
    agent_id: UUID
    incident_id: UUID
    max_retries: int = Field(default=0, ge=0, le=3)
    dry_run: bool = False


class RemediationExecutionDTO(BaseModel):
    action_id: UUID
    accepted: bool
    verified: bool
    status: str
    message: str
    evidence: dict = Field(default_factory=dict)
    decision: str | None = None
    attempts: int = 0
    incident_resolved: bool = False


class AutonomousPreflightDTO(BaseModel):
    action_id: UUID
    agent_id: UUID
    incident_id: UUID
    resource_id: UUID
    lab_only: bool
    resource_is_lab: bool
    agent_autonomous: bool
    policy_autonomous: bool
    writes_enabled: bool
    kill_switch_clear: bool
    eligible: bool
    blockers: list[str] = Field(default_factory=list)


class RemediationSafetyDTO(BaseModel):
    kill_switch_enabled: bool
    writes_enabled: bool
    reason: str | None = None


class RemediationActionDTO(BaseModel):
    id: UUID
    investigation_id: UUID
    resource_id: UUID
    connector_key: str
    action_type: str
    command_preview: str
    risk_level: str
    status: str
    requires_approval: bool
    dry_run: bool


def _to_dto(action):
    return RemediationActionDTO(
        id=action.id,
        investigation_id=action.investigation_id,
        resource_id=action.resource_id,
        connector_key=action.connector_key,
        action_type=action.action_type,
        command_preview=action.command_preview,
        risk_level=action.risk_level.value,
        status=action.status.value,
        requires_approval=action.requires_approval,
        dry_run=action.dry_run,
    )


@router.get("", response_model=list[RemediationActionDTO])
async def list_remediations(
    tenant: TenantContextDep,
    investigation_id: UUID | None = Query(None),
    session: Annotated[AsyncSession, Depends(get_db_session)] = None,
) -> list[RemediationActionDTO]:
    actions = await RemediationActionRepository(session).list(
        tenant.organization_id,
        tenant.workspace_id,
        investigation_id,
    )
    return [_to_dto(action) for action in actions]


@router.get("/safety", response_model=RemediationSafetyDTO)
async def remediation_safety() -> RemediationSafetyDTO:
    from packages.domain.config import NexusSettings
    from packages.remediation.safety import remediation_kill_switch_enabled

    settings = NexusSettings()
    return RemediationSafetyDTO(
        kill_switch_enabled=remediation_kill_switch_enabled(settings),
        writes_enabled=settings.remediation_writes_enabled,
        reason=(
            "Writes are restricted to lab resources"
            if settings.remediation_writes_enabled and settings.remediation_lab_only
            else "Real connector writes are disabled"
        ),
    )


@router.post("/proposals", response_model=RemediationActionDTO, status_code=201)
async def create_remediation_proposal(
    dto: RemediationProposalCreateDTO,
    tenant: TenantContextDep,
    _authorized: TenantContext = Depends(require_permissions("remediation.manage")),
    session: Annotated[AsyncSession, Depends(get_db_session)] = None,
):
    investigation_repo = InvestigationPostgresRepository(session)
    investigation = await investigation_repo.get(
        dto.investigation_id, tenant.organization_id, tenant.workspace_id
    )
    if investigation is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    if investigation.status.value != "completed" or investigation.conclusion is None:
        raise HTTPException(
            status_code=409, detail="Investigation must be completed before remediation"
        )

    resource_repo = CoreRepository(session)
    resource = await resource_repo.get_resource(
        tenant.organization_id, dto.resource_id, tenant.workspace_id
    )
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    evidence_resources = {item.resource_id for item in investigation.evidence if item.resource_id}
    if dto.resource_id not in evidence_resources:
        raise HTTPException(
            status_code=409, detail="Resource is not supported by investigation evidence"
        )
    if resource.resource_type.value != "linux_server":
        raise HTTPException(status_code=400, detail="Only Linux remediation is enabled")

    from packages.remediation.planner import build_restart_service_action

    try:
        action = build_restart_service_action(
            organization_id=tenant.organization_id,
            workspace_id=tenant.workspace_id,
            investigation_id=investigation.id,
            resource_id=resource.id,
            service=dto.service,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    repository = RemediationActionRepository(session)
    await repository.create(action)
    await AuditEventRepository(session).create(
        AuditEvent(
            organization_id=tenant.organization_id,
            workspace_id=tenant.workspace_id,
            actor_type=ActorType.USER,
            actor_id=tenant.user_id,
            event_type=EventType.REMEDIATION_PROPOSED,
            resource_id=resource.id,
            action=action.action_type,
            result_status=ResultStatus.PENDING,
            metadata={
                "action_id": str(action.id),
                "command_preview": action.command_preview,
                "dry_run": action.dry_run,
            },
        )
    )
    await investigation_repo.add_event(
        __import__(
            "packages.investigations.models", fromlist=["InvestigationEvent"]
        ).InvestigationEvent(
            investigation_id=investigation.id,
            event_type="remediation.proposed",
            phase="conclusion",
            metadata={
                "action_id": str(action.id),
                "resource_id": str(resource.id),
                "action_type": action.action_type,
            },
        )
    )
    await session.commit()
    return _to_dto(action)


@router.post(
    "/proposals/automatic",
    response_model=AutomaticRemediationProposalDTO,
    status_code=201,
)
async def create_automatic_remediation_proposal(
    investigation_id: UUID,
    tenant: TenantContextDep,
    _authorized: TenantContext = Depends(require_permissions("remediation.manage")),
    session: Annotated[AsyncSession, Depends(get_db_session)] = None,
):
    investigation = await InvestigationPostgresRepository(session).get(
        investigation_id, tenant.organization_id, tenant.workspace_id
    )
    if investigation is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    try:
        from packages.remediation.auto_proposer import select_validated_restart_action

        action = select_validated_restart_action(investigation)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    repository = RemediationActionRepository(session)
    existing = await repository.list_for_investigation(
        investigation.id, tenant.organization_id, tenant.workspace_id
    )
    if any(
        item.resource_id == action.resource_id and item.action_type == action.action_type
        for item in existing
    ):
        raise HTTPException(
            status_code=409,
            detail="A remediation proposal already exists for this investigation resource",
        )
    await repository.create(action)
    await AuditEventRepository(session).create(
        AuditEvent(
            organization_id=tenant.organization_id,
            workspace_id=tenant.workspace_id,
            actor_type=ActorType.USER,
            actor_id=tenant.user_id,
            event_type=EventType.REMEDIATION_PROPOSED,
            resource_id=action.resource_id,
            action="remediation.auto_proposed",
            result_status=ResultStatus.PENDING,
            metadata={
                "action_id": str(action.id),
                "investigation_id": str(investigation.id),
                "command_preview": action.command_preview,
                "automatic": True,
            },
        )
    )
    await session.commit()
    service = action.command_preview.rsplit(" ", 1)[-1]
    return AutomaticRemediationProposalDTO(
        action_id=action.id,
        investigation_id=action.investigation_id,
        resource_id=action.resource_id,
        action_type=action.action_type,
        service=service,
        risk_level=action.risk_level.value,
        requires_approval=action.requires_approval,
    )


@router.post("/{action_id}/simulate", response_model=RemediationSimulationDTO)
async def simulate_remediation(
    action_id: UUID,
    tenant: TenantContextDep,
    _authorized: TenantContext = Depends(require_permissions("remediation.manage")),
    session: Annotated[AsyncSession, Depends(get_db_session)] = None,
):
    repository = RemediationActionRepository(session)
    action = await repository.get(action_id, tenant.organization_id, tenant.workspace_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Remediation action not found")
    if action.status not in {RemediationStatus.PROPOSED, RemediationStatus.APPROVED}:
        raise HTTPException(status_code=409, detail="Remediation action cannot be simulated")
    resource = await CoreRepository(session).get_resource(
        tenant.organization_id, action.resource_id, tenant.workspace_id
    )
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    from packages.connectors.factory import create_connector
    from packages.remediation.action_specs import build_write_action
    from packages.remediation.executor import RemediationExecutor

    service = action.command_preview.rsplit(" ", 1)[-1]
    connector_action = build_write_action(action.action_type, {"service": service})
    connector = create_connector(resource)
    outcome = await RemediationExecutor(connector).run(
        action, resource, connector_action, dry_run=True
    )
    return RemediationSimulationDTO(
        action_id=outcome.action_id,
        accepted=outcome.accepted,
        simulated=outcome.simulated,
        message=outcome.message,
    )


@router.post("/{action_id}/execute", response_model=RemediationExecutionDTO)
async def execute_remediation(
    action_id: UUID,
    tenant: TenantContextDep,
    principal=Depends(get_current_principal),
    _authorized: TenantContext = Depends(require_permissions("remediation.manage")),
    session: Annotated[AsyncSession, Depends(get_db_session)] = None,
):
    repository = RemediationActionRepository(session)
    action = await repository.get(action_id, tenant.organization_id, tenant.workspace_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Remediation action not found")
    if action.status != RemediationStatus.APPROVED:
        raise HTTPException(status_code=409, detail="Only approved actions can execute")
    resource = await CoreRepository(session).get_resource(
        tenant.organization_id, action.resource_id, tenant.workspace_id
    )
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    from packages.connectors.factory import create_connector
    from packages.remediation.action_specs import build_write_action
    from packages.remediation.executor import RemediationExecutor

    connector = create_connector(resource)
    service = action.command_preview.rsplit(" ", 1)[-1]
    connector_action = build_write_action(action.action_type, {"service": service})
    updated = await repository.update_status(
        action.id, tenant.organization_id, RemediationStatus.EXECUTING, tenant.workspace_id
    )
    await session.commit()
    await connector.connect(resource)
    try:
        outcome = await RemediationExecutor(connector).run(
            updated, resource, connector_action, dry_run=False
        )
        if not outcome.accepted:
            failed = await repository.update_status(
                action.id, tenant.organization_id, RemediationStatus.FAILED, tenant.workspace_id
            )
            await session.commit()
            return RemediationExecutionDTO(
                action_id=action.id,
                accepted=False,
                verified=False,
                status=failed.status.value,
                message=outcome.message,
            )
        await repository.update_status(
            action.id, tenant.organization_id, RemediationStatus.EXECUTED, tenant.workspace_id
        )
        status_result = await connector.execute_read(resource, f"systemctl is-active -- {service}")
        status = (
            (status_result.data or "").strip().splitlines()[0]
            if status_result.success and status_result.data
            else "unknown"
        )
        verified = status in {"active", "running"}
        final_status = RemediationStatus.VERIFIED if verified else RemediationStatus.FAILED
        final = await repository.update_status(
            action.id, tenant.organization_id, final_status, tenant.workspace_id
        )
        await AuditEventRepository(session).create(
            AuditEvent(
                organization_id=tenant.organization_id,
                workspace_id=tenant.workspace_id,
                actor_type=ActorType.USER,
                actor_id=principal.user_id,
                event_type=EventType.TOOL_INVOKED,
                resource_id=resource.id,
                action="remediation.execute",
                result_status=ResultStatus.SUCCESS if verified else ResultStatus.FAILURE,
                metadata={
                    "action_id": str(action.id),
                    "service": service,
                    "status": status,
                    "verified": verified,
                },
            )
        )
        await session.commit()
        return RemediationExecutionDTO(
            action_id=action.id,
            accepted=True,
            verified=verified,
            status=final.status.value,
            message="Remediation executed and verified"
            if verified
            else "Remediation executed but verification failed",
            evidence={"service": service, "status": status},
        )
    finally:
        await connector.disconnect(resource)


@router.get("/{action_id}/autonomous/preflight", response_model=AutonomousPreflightDTO)
async def autonomous_preflight(
    action_id: UUID,
    incident_id: UUID,
    agent_id: UUID,
    tenant: TenantContextDep,
    _authorized: TenantContext = Depends(require_permissions("remediation.manage")),
    session: Annotated[AsyncSession, Depends(get_db_session)] = None,
):
    from packages.domain.config import NexusSettings
    from packages.domain.models.enums import AutonomyLevel, IncidentStatus
    from packages.policies.remediation import evaluate_remediation
    from packages.remediation.safety import check_kill_switch

    action = await RemediationActionRepository(session).get(
        action_id, tenant.organization_id, tenant.workspace_id
    )
    if action is None:
        raise HTTPException(status_code=404, detail="Remediation action not found")
    core = CoreRepository(session)
    agent = await core.get_agent(tenant.organization_id, agent_id, tenant.workspace_id)
    resource = await core.get_resource(
        tenant.organization_id, action.resource_id, tenant.workspace_id
    )
    incident = await IncidentPostgresRepository(session).get(
        incident_id, tenant.organization_id, tenant.workspace_id
    )
    settings = NexusSettings()
    safety = check_kill_switch(settings)
    blockers: list[str] = []
    lab = bool(resource and resource.environment == "lab")
    autonomous = bool(agent and agent.enabled and agent.autonomy_level == AutonomyLevel.AUTONOMOUS)
    if resource is None:
        blockers.append("resource_not_found")
    if incident is None:
        blockers.append("incident_not_found")
    if agent is None:
        blockers.append("agent_not_found")
    if not autonomous:
        blockers.append("agent_not_autonomous")
    if not lab:
        blockers.append("resource_not_lab")
    if incident and incident.status in {IncidentStatus.RESOLVED, IncidentStatus.CLOSED}:
        blockers.append("incident_resolved")
    if incident and incident.investigation_id != action.investigation_id:
        blockers.append("incident_mismatch")
    from packages.domain.models.enums import RiskLevel
    from packages.domain.models.policy import Policy

    policy = (
        Policy(
            organization_id=action.organization_id,
            name="runtime-autonomous-lab",
            max_risk_level=RiskLevel.HIGH,
            allow_autonomous_high_risk=True,
            allowed_resource_ids=[action.resource_id],
        )
        if agent and resource
        else None
    )
    decision = evaluate_remediation(action, agent, policy) if agent and resource else None
    policy_ok = bool(
        decision and decision.execution_mode == "autonomous" and not decision.requires_approval
    )
    if not policy_ok:
        blockers.append("policy_not_autonomous")
    if not settings.remediation_writes_enabled:
        blockers.append("writes_disabled")
    if not safety.allowed:
        blockers.append("kill_switch_active")
    eligible = not blockers
    return AutonomousPreflightDTO(
        action_id=action_id,
        agent_id=agent_id,
        incident_id=incident_id,
        resource_id=action.resource_id,
        lab_only=settings.remediation_lab_only,
        resource_is_lab=lab,
        agent_autonomous=autonomous,
        policy_autonomous=policy_ok,
        writes_enabled=settings.remediation_writes_enabled,
        kill_switch_clear=safety.allowed,
        eligible=eligible,
        blockers=blockers,
    )


@router.post("/{action_id}/autonomous", response_model=RemediationExecutionDTO)
async def execute_autonomous_remediation(
    action_id: UUID,
    dto: AutonomousRemediationRequestDTO,
    tenant: TenantContextDep,
    principal=Depends(get_current_principal),
    _authorized: TenantContext = Depends(require_permissions("remediation.manage")),
    session: Annotated[AsyncSession, Depends(get_db_session)] = None,
):
    from packages.domain.config import NexusSettings
    from packages.domain.models.enums import AutonomyLevel, IncidentStatus
    from packages.remediation.autonomous_service import (
        execute_autonomous_remediation as run_service,
    )
    from packages.remediation.safety import check_kill_switch

    repository = RemediationActionRepository(session)
    action = await repository.get(action_id, tenant.organization_id, tenant.workspace_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Remediation action not found")
    if action.status not in {RemediationStatus.PROPOSED, RemediationStatus.APPROVED}:
        raise HTTPException(
            status_code=409, detail="Remediation action is not eligible for autonomous execution"
        )

    settings = NexusSettings()
    if not dto.dry_run and not settings.remediation_writes_enabled:
        raise HTTPException(status_code=409, detail="Real remediation writes are disabled")
    safety = check_kill_switch(settings)
    if not dto.dry_run and not safety.allowed:
        raise HTTPException(status_code=409, detail=safety.reason or "Remediation is blocked")

    core = CoreRepository(session)
    agent = await core.get_agent(tenant.organization_id, dto.agent_id, tenant.workspace_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    if not agent.enabled:
        raise HTTPException(status_code=409, detail="Agent is disabled")
    if agent.autonomy_level != AutonomyLevel.AUTONOMOUS:
        raise HTTPException(status_code=409, detail="Agent is not autonomous")

    resource = await core.get_resource(
        tenant.organization_id, action.resource_id, tenant.workspace_id
    )
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    if resource.environment != "lab":
        raise HTTPException(
            status_code=409, detail="Autonomous remediation is restricted to lab resources"
        )
    if action.connector_key != "linux":
        raise HTTPException(status_code=400, detail="Unsupported autonomous connector")

    incident_repo = __import__(
        "packages.persistence.repositories.incident", fromlist=["IncidentPostgresRepository"]
    ).IncidentPostgresRepository(session)
    incident = await incident_repo.get(dto.incident_id, tenant.organization_id, tenant.workspace_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    if incident.investigation_id != action.investigation_id:
        raise HTTPException(
            status_code=409, detail="Incident does not belong to remediation investigation"
        )
    if incident.status in {IncidentStatus.RESOLVED, IncidentStatus.CLOSED}:
        raise HTTPException(status_code=409, detail="Incident is already resolved")

    from packages.connectors.factory import create_connector

    connector = create_connector(resource)
    result = await run_service(
        action,
        agent,
        resource,
        connector,
        incident,
        session,
        max_retries=dto.max_retries,
        dry_run=dto.dry_run,
    )
    verified = result.loop.decision == "verified"
    return RemediationExecutionDTO(
        action_id=result.action.id,
        accepted=result.loop.execution.accepted if result.loop.execution else False,
        verified=verified,
        status=result.action.status.value,
        message=result.loop.reason or "Autonomous remediation completed",
        evidence=result.loop.evidence,
        decision=result.loop.decision,
        attempts=result.loop.attempts,
        incident_resolved=result.incident_resolved,
    )


@router.post("/{action_id}/reject", response_model=RemediationActionDTO)
async def reject_remediation(
    action_id: UUID,
    tenant: TenantContextDep,
    principal=Depends(get_current_principal),
    _authorized: TenantContext = Depends(require_permissions("remediation.manage")),
    session: Annotated[AsyncSession, Depends(get_db_session)] = None,
):
    repository = RemediationActionRepository(session)
    action = await repository.get(action_id, tenant.organization_id, tenant.workspace_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Remediation action not found")
    if action.status != RemediationStatus.PROPOSED:
        raise HTTPException(status_code=409, detail="Only proposed actions can be rejected")
    updated = await repository.update_status(
        action.id, tenant.organization_id, RemediationStatus.REJECTED, tenant.workspace_id
    )
    await AuditEventRepository(session).create(
        AuditEvent(
            organization_id=tenant.organization_id,
            workspace_id=tenant.workspace_id,
            actor_type=ActorType.USER,
            actor_id=principal.user_id,
            event_type=EventType.REMEDIATION_REJECTED,
            resource_id=action.resource_id,
            action=action.action_type,
            result_status=ResultStatus.SUCCESS,
            metadata={"action_id": str(action.id)},
        )
    )
    await session.commit()
    return _to_dto(updated)


@router.post("/{action_id}/approve", response_model=RemediationActionDTO)
async def approve_remediation(
    action_id: UUID,
    tenant: TenantContextDep,
    principal=Depends(get_current_principal),
    _authorized: TenantContext = Depends(require_permissions("remediation.manage")),
    session: Annotated[AsyncSession, Depends(get_db_session)] = None,
):
    repository = RemediationActionRepository(session)
    action = await repository.get(action_id, tenant.organization_id, tenant.workspace_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Remediation action not found")
    if action.status != RemediationStatus.PROPOSED:
        raise HTTPException(
            status_code=409, detail="Remediation action is no longer pending approval"
        )
    updated = await repository.update_status(
        action.id, tenant.organization_id, RemediationStatus.APPROVED, tenant.workspace_id
    )
    investigation_repo = InvestigationPostgresRepository(session)
    await AuditEventRepository(session).create(
        AuditEvent(
            organization_id=tenant.organization_id,
            workspace_id=tenant.workspace_id,
            actor_type=ActorType.USER,
            actor_id=principal.user_id,
            event_type=EventType.REMEDIATION_APPROVED,
            resource_id=action.resource_id,
            action=action.action_type,
            result_status=ResultStatus.SUCCESS,
            metadata={"action_id": str(action.id), "dry_run": action.dry_run},
        )
    )
    await investigation_repo.add_event(
        __import__(
            "packages.investigations.models", fromlist=["InvestigationEvent"]
        ).InvestigationEvent(
            investigation_id=action.investigation_id,
            event_type="remediation.approved",
            phase="conclusion",
            metadata={
                "action_id": str(action.id),
                "approved_by": str(principal.user_id),
                "dry_run": action.dry_run,
            },
        )
    )
    await session.commit()
    return _to_dto(updated)
