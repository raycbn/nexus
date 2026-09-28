from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from packages.auth import get_tenant_context
from packages.domain.models.context import TenantContext
from packages.persistence.repositories.audit import AuditEventRepository
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db_session

router = APIRouter(prefix="/audit", tags=["audit"])
TenantContextDep = Annotated[TenantContext, Depends(get_tenant_context)]


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
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: Any


class AuditEventListResponseDTO(BaseModel):
    events: list[AuditEventDTO]
    total: int
    limit: int
    offset: int


def _to_dto(event) -> AuditEventDTO:
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


@router.get("", response_model=AuditEventListResponseDTO)
async def list_audit_events(
    tenant: TenantContextDep,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    actor_type: str | None = Query(None),
    event_type: str | None = Query(None),
    resource_id: UUID | None = Query(None),
    result_status: str | None = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> AuditEventListResponseDTO:
    repository = AuditEventRepository(session)
    events, total = await repository.list(
        organization_id=tenant.organization_id,
        limit=limit,
        offset=offset,
        actor_type=actor_type,
        event_type=event_type,
        resource_id=resource_id,
        result_status=result_status,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return AuditEventListResponseDTO(
        events=[_to_dto(event) for event in events],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{event_id}", response_model=AuditEventDTO)
async def get_audit_event(
    event_id: UUID,
    tenant: TenantContextDep,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuditEventDTO:
    repository = AuditEventRepository(session)
    event = await repository.get(tenant.organization_id, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Audit event not found")
    return _to_dto(event)
