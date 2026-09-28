import asyncio
import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from packages.auth import get_current_principal, get_tenant_context, require_roles
from packages.domain.models.context import TenantContext
from packages.domain.models.enums import ActorType, Severity
from packages.incidents.engine import IncidentEngine
from packages.investigations.models import Investigation, InvestigationEvent
from packages.persistence.database import get_session
from packages.persistence.repositories.audit import AuditEventRepository
from packages.persistence.repositories.core import CoreRepository
from packages.persistence.repositories.incident import IncidentPostgresRepository
from packages.persistence.repositories.investigation import InvestigationPostgresRepository
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db_session
from apps.api.models import (
    ConclusionDTO,
    EvidenceDTO,
    HypothesisDTO,
    InvestigationCreateDTO,
    InvestigationDetailDTO,
    InvestigationEventDTO,
    ValidationDTO,
)
from apps.api.services.investigation_service import InvestigationApplicationService
from apps.api.services.targeted_investigation_service import TargetedInvestigationApplicationService

router = APIRouter(prefix="/investigations", tags=["investigations"])

TenantContextDep = Annotated[TenantContext, Depends(get_tenant_context)]


class InvestigationIncidentCreateDTO(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1)
    severity: str | None = Field(default=None, pattern="^(low|medium|high|critical)$")
    affected_resource_ids: list[UUID] | None = None


class InvestigationIncidentSuggestionDTO(BaseModel):
    title: str
    description: str
    severity: str
    affected_resource_ids: list[UUID]
    should_create: bool
    reasons: list[str]


class InvestigationIncidentResponseDTO(BaseModel):
    id: UUID


def get_investigation_service(
    tenant: TenantContextDep,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> InvestigationApplicationService:
    return InvestigationApplicationService(tenant_context=tenant, session=session)


@router.get("", response_model=list[InvestigationDetailDTO])
async def list_investigations(
    tenant: TenantContextDep,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    status: list[str] | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[InvestigationDetailDTO]:
    repository = InvestigationPostgresRepository(session)
    investigations = await repository.list(
        organization_id=tenant.organization_id,
        workspace_id=tenant.workspace_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return [_investigation_to_detail(item) for item in investigations]


@router.get("/{investigation_id}", response_model=InvestigationDetailDTO)
async def get_investigation(
    investigation_id: UUID,
    tenant: TenantContextDep,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> InvestigationDetailDTO:
    repository = InvestigationPostgresRepository(session)
    investigation = await repository.get(
        investigation_id, tenant.organization_id, tenant.workspace_id
    )
    if investigation is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return _investigation_to_detail(investigation)


@router.get(
    "/{investigation_id}/events",
    response_model=list[InvestigationEventDTO],
)
async def list_investigation_events(
    investigation_id: UUID,
    tenant: TenantContextDep,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: int = Query(100, ge=1, le=500),
) -> list[InvestigationEventDTO]:
    repository = InvestigationPostgresRepository(session)
    events = await repository.list_events(
        investigation_id,
        tenant.organization_id,
        tenant.workspace_id,
        limit=limit,
    )
    return [
        InvestigationEventDTO(
            id=event.id,
            investigation_id=event.investigation_id,
            event_type=event.event_type,
            phase=event.phase,
            metadata=event.metadata,
            created_at=event.created_at,
        )
        for event in events
    ]


@router.get(
    "/{investigation_id}/events/stream",
    response_class=StreamingResponse,
)
async def stream_investigation_events(
    investigation_id: UUID,
    tenant: TenantContextDep,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    last_event_id: Annotated[UUID | None, Header(alias="Last-Event-ID")] = None,
):
    repository = InvestigationPostgresRepository(session)
    investigation = await repository.get(
        investigation_id, tenant.organization_id, tenant.workspace_id
    )
    if investigation is None:
        raise HTTPException(status_code=404, detail="Investigation not found")

    async def event_generator():
        last_created_at = None
        while True:
            events = await repository.list_events(
                investigation_id,
                tenant.organization_id,
                tenant.workspace_id,
                limit=500,
                after_id=last_event_id,
            )
            for event in events:
                if last_created_at is not None and event.created_at <= last_created_at:
                    continue
                last_created_at = event.created_at
                payload = {
                    "id": str(event.id),
                    "investigation_id": str(event.investigation_id),
                    "event_type": event.event_type,
                    "phase": event.phase,
                    "metadata": event.metadata,
                    "created_at": event.created_at.isoformat(),
                }
                yield f"id: {event.id}\nevent: investigation\ndata: {json.dumps(payload)}\n\n"
            current = await repository.get(
                investigation_id, tenant.organization_id, tenant.workspace_id
            )
            if current is None or current.status.value in {"completed", "failed"}:
                yield "event: complete\ndata: {}\n\n"
                break
            yield ": heartbeat\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get(
    "/{investigation_id}/incident/suggestion",
    response_model=InvestigationIncidentSuggestionDTO,
)
async def suggest_incident_from_investigation(
    investigation_id: UUID,
    tenant: TenantContextDep,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> InvestigationIncidentSuggestionDTO:
    repository = InvestigationPostgresRepository(session)
    investigation = await repository.get(
        investigation_id, tenant.organization_id, tenant.workspace_id
    )
    if investigation is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    suggestion = IncidentEngine.suggest_incident_from_investigation(investigation)
    return InvestigationIncidentSuggestionDTO(
        title=suggestion.title,
        description=suggestion.description,
        severity=suggestion.severity.value,
        affected_resource_ids=suggestion.affected_resource_ids,
        should_create=suggestion.should_create,
        reasons=suggestion.reasons,
    )


@router.post(
    "/{investigation_id}/incident",
    response_model=InvestigationIncidentResponseDTO,
    status_code=201,
)
async def create_incident_from_investigation(
    investigation_id: UUID,
    dto: InvestigationIncidentCreateDTO,
    tenant: TenantContextDep,
    principal=Depends(get_current_principal),
    _authorized: TenantContext = Depends(require_roles("admin", "operator")),
    session: Annotated[AsyncSession, Depends(get_db_session)] = None,
):
    repository = InvestigationPostgresRepository(session)
    investigation = await repository.get(
        investigation_id, tenant.organization_id, tenant.workspace_id
    )
    if investigation is None:
        raise HTTPException(status_code=404, detail="Investigation not found")

    suggestion = IncidentEngine.suggest_incident_from_investigation(investigation)
    if not suggestion.should_create:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Investigation is not ready to become an incident",
                "reasons": suggestion.reasons,
            },
        )
    if not suggestion.affected_resource_ids and not dto.affected_resource_ids:
        raise HTTPException(
            status_code=400,
            detail=(
                "Affected resource IDs are required when the investigation has no resource evidence"
            ),
        )
    engine = IncidentEngine(
        repository=IncidentPostgresRepository(session),
        tenant_context=tenant,
        audit_repository=AuditEventRepository(session),
    )
    incident = await engine.create_incident_from_investigation(
        title=dto.title or suggestion.title,
        description=dto.description or suggestion.description,
        severity=Severity(dto.severity or suggestion.severity.value),
        affected_resource_ids=dto.affected_resource_ids or suggestion.affected_resource_ids,
        investigation=investigation,
        actor_id=principal.user_id,
        actor_type=ActorType.USER,
    )
    return {"id": incident.id}


async def _run_investigation_background(
    investigation_id: UUID, objective: str, tenant: TenantContext
) -> None:
    async with get_session() as session:
        repository = InvestigationPostgresRepository(session)
        investigation = await repository.get(
            investigation_id, tenant.organization_id, tenant.workspace_id
        )
        if investigation is None:
            return
        service = InvestigationApplicationService(tenant_context=tenant, session=session)
        try:
            await service.run_investigation(objective, investigation=investigation)
        except Exception:
            investigation.status = "failed"
            investigation.phase = "failed"
            await repository.update(investigation, tenant.organization_id, tenant.workspace_id)
            raise


@router.post("", response_model=InvestigationDetailDTO, status_code=202)
async def create_investigation(
    background_tasks: BackgroundTasks,
    tenant: Annotated[TenantContext, Depends(require_roles("admin", "operator"))],
    dto: InvestigationCreateDTO,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> InvestigationDetailDTO:
    """Create an investigation and execute it asynchronously."""
    objective = dto.objective.strip()
    if not objective:
        raise HTTPException(status_code=422, detail="Investigation objective cannot be empty")
    repository = InvestigationPostgresRepository(session)
    investigation = Investigation(
        organization_id=tenant.organization_id,
        workspace_id=tenant.workspace_id,
        objective=objective,
    )
    investigation = await repository.create(investigation)
    await repository.add_event(
        InvestigationEvent(
            investigation_id=investigation.id,
            event_type="investigation.started",
            phase=investigation.phase,
        )
    )
    await session.commit()
    background_tasks.add_task(_run_investigation_background, investigation.id, objective, tenant)
    return _investigation_to_detail(investigation)


def _investigation_to_detail(investigation: Investigation) -> InvestigationDetailDTO:
    evidence = [
        EvidenceDTO(
            id=e.id,
            source_tool=e.source_tool,
            resource_id=e.resource_id,
            observed_value=e.observed_value,
            mode=e.mode,
            relevance=e.relevance,
            created_at=e.timestamp,
        )
        for e in investigation.evidence
    ]

    hypotheses = [
        HypothesisDTO(
            id=h.id,
            text=h.text,
            supporting_evidence_ids=h.supporting_evidence_ids,
            contradicting_evidence_ids=h.contradicting_evidence_ids,
            status=h.status.value,
        )
        for h in investigation.hypotheses
    ]

    validations = [
        ValidationDTO(
            id=v.id,
            action_tool=v.action_tool,
            expected_condition=v.expected_condition,
            actual_result=v.actual_result,
            passed=v.passed,
        )
        for v in investigation.validations
    ]

    conclusion = None
    if investigation.conclusion:
        conclusion = ConclusionDTO(
            finding=investigation.conclusion.finding,
            confidence=investigation.conclusion.confidence,
            supporting_evidence_ids=investigation.conclusion.supporting_evidence_ids,
            unresolved_uncertainty=investigation.conclusion.unresolved_uncertainty,
        )

    return InvestigationDetailDTO(
        id=investigation.id,
        objective=investigation.objective,
        status=investigation.status.value,
        phase=investigation.phase,
        started_at=investigation.started_at,
        completed_at=investigation.completed_at,
        evidence=evidence,
        hypotheses=hypotheses,
        validations=validations,
        conclusion=conclusion,
    )


async def _run_targeted_investigation_background(
    investigation_id: UUID,
    objective: str,
    tenant: TenantContext,
    resource_id: UUID,
) -> None:
    async with get_session() as session:
        repository = InvestigationPostgresRepository(session)
        investigation = await repository.get(
            investigation_id, tenant.organization_id, tenant.workspace_id
        )
        if investigation is None:
            return
        service = TargetedInvestigationApplicationService(
            tenant_context=tenant,
            session=session,
            resource_id=resource_id,
        )
        try:
            await service.run_investigation(objective, investigation=investigation)
        except Exception:
            investigation.status = "failed"
            investigation.phase = "failed"
            await repository.update(investigation, tenant.organization_id, tenant.workspace_id)
            raise


@router.post("/targeted", response_model=InvestigationDetailDTO, status_code=202)
async def create_targeted_investigation(
    background_tasks: BackgroundTasks,
    tenant: Annotated[TenantContext, Depends(require_roles("admin", "operator"))],
    dto: InvestigationCreateDTO,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> InvestigationDetailDTO:
    """Create a read-only investigation pinned to one resource."""
    if dto.resource_id is None:
        raise HTTPException(status_code=422, detail="resource_id is required")
    resource = await CoreRepository(session).get_resource(
        tenant.organization_id, dto.resource_id, tenant.workspace_id
    )
    if resource is None or not resource.enabled:
        raise HTTPException(status_code=404, detail="Investigation resource not found")
    objective = dto.objective.strip()
    repository = InvestigationPostgresRepository(session)
    investigation = Investigation(
        organization_id=tenant.organization_id,
        workspace_id=tenant.workspace_id,
        objective=objective,
    )
    investigation = await repository.create(investigation)
    await repository.add_event(
        InvestigationEvent(
            investigation_id=investigation.id,
            event_type="investigation.started",
            phase=investigation.phase,
            metadata={"resource_id": str(resource.id)},
        )
    )
    await session.commit()
    background_tasks.add_task(
        _run_targeted_investigation_background,
        investigation.id,
        objective,
        tenant,
        resource.id,
    )
    return _investigation_to_detail(investigation)
