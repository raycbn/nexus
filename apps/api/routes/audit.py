from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from packages.domain.models.audit_event import AuditEvent
from pydantic import BaseModel

router = APIRouter(prefix="/audit", tags=["audit"])


# In-memory store for development
_audit_events: list[AuditEvent] = []


class AuditEventDTO(BaseModel):
    id: UUID
    organization_id: UUID
    workspace_id: UUID | None = None
    actor_type: str
    actor_id: UUID
    event_type: str
    resource_id: UUID | None = None
    tool_id: UUID | None = None
    action: str
    result_status: str
    metadata: dict[str, Any]
    created_at: Any


class AuditEventListResponseDTO(BaseModel):
    events: list[AuditEventDTO]
    total: int
    limit: int
    offset: int


@router.get("", response_model=AuditEventListResponseDTO)
async def list_audit_events(
    actor_type: str | None = Query(None),
    event_type: str | None = Query(None),
    resource_id: UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> AuditEventListResponseDTO:
    events = list(_audit_events)

    if actor_type:
        events = [e for e in events if e.actor_type.value == actor_type]
    if event_type:
        events = [e for e in events if e.event_type.value == event_type]
    if resource_id:
        events = [e for e in events if e.resource_id == resource_id]

    events.sort(key=lambda x: x.created_at, reverse=True)
    total = len(events)
    events = events[offset : offset + limit]

    return AuditEventListResponseDTO(
        events=[
            AuditEventDTO(
                id=e.id,
                organization_id=e.organization_id,
                workspace_id=e.workspace_id,
                actor_type=e.actor_type.value,
                actor_id=e.actor_id,
                event_type=e.event_type.value,
                resource_id=e.resource_id,
                tool_id=e.tool_id,
                action=e.action,
                result_status=e.result_status.value,
                metadata=e.metadata,
                created_at=e.created_at,
            )
            for e in events
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{event_id}", response_model=AuditEventDTO)
async def get_audit_event(event_id: UUID) -> AuditEventDTO:
    event = next((e for e in _audit_events if e.id == event_id), None)
    if not event:
        raise HTTPException(status_code=404, detail="Audit event not found")
    return AuditEventDTO(
        id=event.id,
        organization_id=event.organization_id,
        workspace_id=event.workspace_id,
        actor_type=event.actor_type.value,
        actor_id=event.actor_id,
        event_type=event.event_type.value,
        resource_id=event.resource_id,
        tool_id=event.tool_id,
        action=event.action,
        result_status=event.result_status.value,
        metadata=event.metadata,
        created_at=event.created_at,
    )
