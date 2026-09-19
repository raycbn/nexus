from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from packages.domain.models.agent import Agent
from packages.domain.models.audit_event import AuditEvent
from packages.domain.models.enums import ActorType
from packages.domain.models.incident import (
    Incident,
    IncidentStatus,
    Severity,
)
from packages.domain.models.resource import Resource
from packages.incidents.engine import IncidentEngine
from packages.incidents.in_memory_repository import InMemoryIncidentRepository
from pydantic import BaseModel, Field

router = APIRouter(prefix="/incidents", tags=["incidents"])


# In-memory stores for development
_incident_repository: InMemoryIncidentRepository | None = None
_incident_engine: IncidentEngine | None = None
_resources: dict[UUID, Resource] = {}
_agents: dict[UUID, Agent] = {}
_audit_events: list[AuditEvent] = []
_organization_id = uuid4()
_workspace_id = uuid4()


def get_incident_repository() -> InMemoryIncidentRepository:
    global _incident_repository
    if _incident_repository is None:
        _incident_repository = InMemoryIncidentRepository()
    return _incident_repository


def get_incident_engine(
    repo: InMemoryIncidentRepository = Depends(get_incident_repository),
) -> IncidentEngine:
    global _incident_engine
    if _incident_engine is None:
        _incident_engine = IncidentEngine(
            repository=repo,
            organization_id=_organization_id,
            workspace_id=_workspace_id,
        )
    return _incident_engine


# DTOs
class IncidentTimelineEntryDTO(BaseModel):
    id: UUID
    incident_id: UUID
    event_type: str
    actor_type: str
    actor_id: UUID | None = None
    description: str
    related_tool: str | None = None
    related_resource_id: UUID | None = None
    related_investigation_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class IncidentSummaryDTO(BaseModel):
    id: UUID
    title: str
    description: str
    severity: str
    status: str
    affected_resource_ids: list[UUID]
    assigned_agent_id: UUID | None = None
    investigation_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None


class IncidentDetailDTO(BaseModel):
    id: UUID
    title: str
    description: str
    severity: str
    status: str
    affected_resource_ids: list[UUID]
    assigned_agent_id: UUID | None = None
    investigation_id: UUID | None = None
    evidence_ids: list[UUID]
    conclusion_finding: str | None = None
    conclusion_confidence: float | None = None
    conclusion_uncertainty: str | None = None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None
    timeline: list[IncidentTimelineEntryDTO]
    audit_event_ids: list[UUID]


class IncidentCreateDTO(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    severity: str = Field(pattern="^(low|medium|high|critical)$")
    affected_resource_ids: list[UUID] = Field(min_length=1)


class IncidentStatusUpdateDTO(BaseModel):
    status: str = Field(pattern="^(detected|investigating|identified|monitoring|resolved|closed)$")


class IncidentSeverityUpdateDTO(BaseModel):
    severity: str = Field(pattern="^(low|medium|high|critical)$")


class IncidentListResponseDTO(BaseModel):
    incidents: list[IncidentSummaryDTO]
    total: int
    limit: int
    offset: int


def _map_severity(s: str) -> Severity:
    return Severity(s)


def _map_status(s: str) -> IncidentStatus:
    return IncidentStatus(s)


def _incident_to_summary(incident: Incident) -> IncidentSummaryDTO:
    return IncidentSummaryDTO(
        id=incident.id,
        title=incident.title,
        description=incident.description,
        severity=incident.severity.value,
        status=incident.status.value,
        affected_resource_ids=incident.affected_resource_ids,
        assigned_agent_id=incident.assigned_agent_id,
        investigation_id=incident.investigation_id,
        created_at=incident.created_at,
        updated_at=incident.updated_at,
        started_at=incident.started_at,
        resolved_at=incident.resolved_at,
        closed_at=incident.closed_at,
    )


def _incident_to_detail(incident: Incident) -> IncidentDetailDTO:
    return IncidentDetailDTO(
        id=incident.id,
        title=incident.title,
        description=incident.description,
        severity=incident.severity.value,
        status=incident.status.value,
        affected_resource_ids=incident.affected_resource_ids,
        assigned_agent_id=incident.assigned_agent_id,
        investigation_id=incident.investigation_id,
        evidence_ids=incident.evidence_ids,
        conclusion_finding=incident.conclusion_finding,
        conclusion_confidence=incident.conclusion_confidence,
        conclusion_uncertainty=incident.conclusion_uncertainty,
        created_at=incident.created_at,
        updated_at=incident.updated_at,
        started_at=incident.started_at,
        resolved_at=incident.resolved_at,
        closed_at=incident.closed_at,
        timeline=[
            IncidentTimelineEntryDTO(
                id=entry.id,
                incident_id=entry.incident_id,
                event_type=entry.event_type.value,
                actor_type=entry.actor_type,
                actor_id=entry.actor_id,
                description=entry.description,
                related_tool=entry.related_tool,
                related_resource_id=entry.related_resource_id,
                related_investigation_id=entry.related_investigation_id,
                metadata=entry.metadata,
                created_at=entry.created_at,
            )
            for entry in incident.timeline
        ],
        audit_event_ids=incident.audit_event_ids,
    )


@router.get("", response_model=IncidentListResponseDTO)
async def list_incidents(
    status: list[str] | None = Query(None),
    severity: list[str] | None = Query(None),
    search: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("updated_at"),
    sort_order: str = Query("desc"),
    engine: IncidentEngine = Depends(get_incident_engine),
) -> IncidentListResponseDTO:
    incidents = await engine.list_incidents(
        workspace_id=_workspace_id,
        status=status,
        severity=severity,
        search=search,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    total = await engine.count_incidents(
        workspace_id=_workspace_id,
        status=status,
        severity=severity,
        search=search,
    )
    return IncidentListResponseDTO(
        incidents=[_incident_to_summary(inc) for inc in incidents],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=IncidentDetailDTO, status_code=201)
async def create_incident(
    dto: IncidentCreateDTO,
    engine: IncidentEngine = Depends(get_incident_engine),
) -> IncidentDetailDTO:
    try:
        severity = _map_severity(dto.severity)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid severity: {dto.severity}") from e

    actor_id = uuid4()  # In real impl, get from auth context
    incident = await engine.create_incident(
        title=dto.title,
        description=dto.description,
        severity=severity,
        affected_resource_ids=dto.affected_resource_ids,
        actor_id=actor_id,
        actor_type=ActorType.SYSTEM,
    )

    if not incident:
        raise HTTPException(status_code=500, detail="Failed to create incident")

    return _incident_to_detail(incident)


@router.get("/{incident_id}", response_model=IncidentDetailDTO)
async def get_incident(
    incident_id: UUID,
    engine: IncidentEngine = Depends(get_incident_engine),
) -> IncidentDetailDTO:
    incident = await engine.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return _incident_to_detail(incident)


@router.get("/{incident_id}/timeline", response_model=list[IncidentTimelineEntryDTO])
async def get_incident_timeline(
    incident_id: UUID,
    engine: IncidentEngine = Depends(get_incident_engine),
) -> list[IncidentTimelineEntryDTO]:
    incident = await engine.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return [
        IncidentTimelineEntryDTO(
            id=entry.id,
            incident_id=entry.incident_id,
            event_type=entry.event_type.value,
            actor_type=entry.actor_type,
            actor_id=entry.actor_id,
            description=entry.description,
            related_tool=entry.related_tool,
            related_resource_id=entry.related_resource_id,
            related_investigation_id=entry.related_investigation_id,
            metadata=entry.metadata,
            created_at=entry.created_at,
        )
        for entry in incident.timeline
    ]


@router.post("/{incident_id}/transition", response_model=IncidentDetailDTO)
async def transition_incident_status(
    incident_id: UUID,
    dto: IncidentStatusUpdateDTO,
    engine: IncidentEngine = Depends(get_incident_engine),
) -> IncidentDetailDTO:
    try:
        new_status = _map_status(dto.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid status: {dto.status}") from e

    actor_id = uuid4()  # In real impl, get from auth context
    incident = await engine.transition_status(
        incident_id=incident_id,
        new_status=new_status,
        actor_id=actor_id,
        actor_type=ActorType.SYSTEM,
    )

    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found or invalid transition")

    return _incident_to_detail(incident)


@router.post("/{incident_id}/severity", response_model=IncidentDetailDTO)
async def update_incident_severity(
    incident_id: UUID,
    dto: IncidentSeverityUpdateDTO,
    engine: IncidentEngine = Depends(get_incident_engine),
) -> IncidentDetailDTO:
    try:
        severity = _map_severity(dto.severity)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid severity: {dto.severity}") from e

    actor_id = uuid4()  # In real impl, get from auth context
    incident = await engine.set_severity(
        incident_id=incident_id,
        severity=severity,
        actor_id=actor_id,
        actor_type=ActorType.SYSTEM,
    )

    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    return _incident_to_detail(incident)


@router.post("/{incident_id}/resolve", response_model=IncidentDetailDTO)
async def resolve_incident(
    incident_id: UUID,
    engine: IncidentEngine = Depends(get_incident_engine),
) -> IncidentDetailDTO:
    actor_id = uuid4()
    incident = await engine.resolve_incident(
        incident_id=incident_id,
        actor_id=actor_id,
        actor_type=ActorType.SYSTEM,
    )

    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found or invalid transition")

    return _incident_to_detail(incident)


@router.post("/{incident_id}/close", response_model=IncidentDetailDTO)
async def close_incident(
    incident_id: UUID,
    engine: IncidentEngine = Depends(get_incident_engine),
) -> IncidentDetailDTO:
    actor_id = uuid4()
    incident = await engine.close_incident(
        incident_id=incident_id,
        actor_id=actor_id,
        actor_type=ActorType.SYSTEM,
    )

    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found or invalid transition")

    return _incident_to_detail(incident)
