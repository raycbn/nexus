from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from packages.auth import require_permissions
from packages.domain.models.context import TenantContext
from packages.persistence.repositories.usage import UsageRepository
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db_session

router = APIRouter(prefix="/metering", tags=["metering"])


class UsageEventCreateDTO(BaseModel):
    metric: str = Field(min_length=1, max_length=100)
    quantity: float = Field(gt=0)
    source: str = Field(min_length=1, max_length=100)
    dimensions: dict[str, str] = Field(default_factory=dict)
    occurred_at: datetime | None = None


class UsageEventDTO(BaseModel):
    id: UUID
    metric: str
    quantity: float
    source: str
    dimensions: dict[str, str]
    occurred_at: datetime


class UsageSummaryDTO(BaseModel):
    metric: str
    quantity: float


@router.post("/events", response_model=UsageEventDTO, status_code=201)
async def record_usage(
    dto: UsageEventCreateDTO,
    tenant: Annotated[TenantContext, Depends(require_permissions("metering.manage"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UsageEventDTO:
    event = await UsageRepository(session).record(
        tenant.organization_id,
        tenant.workspace_id,
        dto.metric,
        dto.quantity,
        dto.source,
        dto.dimensions,
        dto.occurred_at,
    )
    await session.commit()
    return UsageEventDTO.model_validate(event, from_attributes=True)


@router.get("/summary", response_model=list[UsageSummaryDTO])
async def usage_summary(
    tenant: Annotated[TenantContext, Depends(require_permissions("metering.read"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    days: int = Query(30, ge=1, le=365),
) -> list[UsageSummaryDTO]:
    end = datetime.now(UTC)
    start = end - timedelta(days=days)
    rows = await UsageRepository(session).summary(
        tenant.organization_id, tenant.workspace_id, start, end
    )
    return [UsageSummaryDTO(metric=metric, quantity=quantity) for metric, quantity in rows]


@router.get("/events", response_model=list[UsageEventDTO])
async def list_usage_events(
    tenant: Annotated[TenantContext, Depends(require_permissions("metering.read"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: int = Query(50, ge=1, le=100),
) -> list[UsageEventDTO]:
    events = await UsageRepository(session).list_events(
        tenant.organization_id, tenant.workspace_id, limit
    )
    return [UsageEventDTO.model_validate(event, from_attributes=True) for event in events]
