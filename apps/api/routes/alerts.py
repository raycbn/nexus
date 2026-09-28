from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from packages.auth import get_current_principal, require_permissions
from packages.domain.models.context import TenantContext
from packages.domain.models.identity import AuthenticatedPrincipal
from packages.persistence.repositories.alert import AlertRepository
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db_session

router = APIRouter(prefix="/alerts", tags=["alerts"])


class AlertCreateDTO(BaseModel):
    source: str = Field(min_length=1, max_length=100)
    external_id: str | None = Field(default=None, max_length=255)
    dedup_key: str = Field(min_length=1, max_length=512)
    correlation_key: str | None = Field(default=None, max_length=512)
    title: str = Field(min_length=1, max_length=255)
    message: str = Field(min_length=1)
    severity: str = Field(pattern="^(low|medium|high|critical)$")


class AlertStatusDTO(BaseModel):
    status: str = Field(pattern="^(open|acknowledged|resolved)$")


class AlertDTO(BaseModel):
    id: UUID
    source: str
    external_id: str | None
    dedup_key: str
    correlation_key: str | None
    title: str
    message: str
    severity: str
    status: str
    occurrence_count: int
    first_seen_at: datetime
    last_seen_at: datetime
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    incident_id: UUID | None
    created_at: datetime
    updated_at: datetime


def _dto(alert) -> AlertDTO:
    return AlertDTO.model_validate(alert, from_attributes=True)


@router.get("", response_model=list[AlertDTO])
async def list_alerts(
    tenant: Annotated[TenantContext, Depends(require_permissions("alerts.read"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[AlertDTO]:
    alerts = await AlertRepository(session).list(
        tenant.organization_id, tenant.workspace_id, status, limit, offset
    )
    return [_dto(alert) for alert in alerts]


@router.post("", response_model=AlertDTO, status_code=201)
async def ingest_alert(
    dto: AlertCreateDTO,
    tenant: Annotated[TenantContext, Depends(require_permissions("alerts.manage"))],
    _principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AlertDTO:
    alert = await AlertRepository(session).ingest(
        tenant.organization_id, tenant.workspace_id, **dto.model_dump()
    )
    await session.commit()
    return _dto(alert)


@router.post("/{alert_id}/status", response_model=AlertDTO)
async def update_alert_status(
    alert_id: UUID,
    dto: AlertStatusDTO,
    tenant: Annotated[TenantContext, Depends(require_permissions("alerts.manage"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AlertDTO:
    repo = AlertRepository(session)
    alert = await repo.get(alert_id, tenant.organization_id)
    if alert is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Alert not found")
    alert = await repo.set_status(alert, dto.status)
    await session.commit()
    return _dto(alert)
