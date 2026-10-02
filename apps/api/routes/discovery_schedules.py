from datetime import datetime
from uuid import UUID

from croniter import croniter
from fastapi import APIRouter, Depends, HTTPException, status
from packages.auth import require_permissions
from packages.billing.entitlements import enforce_feature
from packages.domain.models.context import TenantContext
from packages.persistence.repositories.core import CoreRepository
from packages.persistence.repositories.discovery_schedule import DiscoveryScheduleRepository
from packages.persistence.repositories.resource_connections import ResourceConnectionRepository
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db_session

router = APIRouter(prefix="/discovery-schedules", tags=["discovery-schedules"])


class DiscoveryScheduleDTO(BaseModel):
    id: UUID
    resource_id: UUID
    cron_expression: str
    timezone: str
    enabled: bool
    next_run_at: datetime | None
    last_run_at: datetime | None
    last_job_id: UUID | None
    created_at: datetime
    updated_at: datetime


class DiscoveryScheduleCreateDTO(BaseModel):
    resource_id: UUID
    cron_expression: str = Field(min_length=5, max_length=128)
    timezone: str = Field(default="UTC", min_length=1, max_length=64)


class DiscoveryScheduleUpdateDTO(BaseModel):
    cron_expression: str | None = Field(default=None, min_length=5, max_length=128)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    enabled: bool | None = None


def _next_run(cron_expression: str, timezone: str) -> datetime:

    from zoneinfo import ZoneInfo

    try:
        tz = ZoneInfo(timezone)
        base = datetime.now(tz)
        return croniter(cron_expression, base).get_next(datetime).astimezone(ZoneInfo("UTC"))
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid schedule: {exc}") from exc


def _dto(model) -> DiscoveryScheduleDTO:
    return DiscoveryScheduleDTO.model_validate(model, from_attributes=True)


@router.get("", response_model=list[DiscoveryScheduleDTO])
async def list_schedules(
    tenant: TenantContext = Depends(require_permissions("discovery.read")),
    session: AsyncSession = Depends(get_db_session),
) -> list[DiscoveryScheduleDTO]:
    schedules = await DiscoveryScheduleRepository(session).list_for_workspace(
        tenant.organization_id, tenant.workspace_id
    )
    return [_dto(item) for item in schedules]


@router.get("/{schedule_id}", response_model=DiscoveryScheduleDTO)
async def get_schedule(
    schedule_id: UUID,
    tenant: TenantContext = Depends(require_permissions("discovery.read")),
    session: AsyncSession = Depends(get_db_session),
) -> DiscoveryScheduleDTO:
    schedule = await DiscoveryScheduleRepository(session).get(
        tenant.organization_id, schedule_id, tenant.workspace_id
    )
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return _dto(schedule)


@router.post("", response_model=DiscoveryScheduleDTO, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    payload: DiscoveryScheduleCreateDTO,
    tenant: TenantContext = Depends(require_permissions("discovery.manage")),
    session: AsyncSession = Depends(get_db_session),
) -> DiscoveryScheduleDTO:
    await enforce_feature(session, tenant.organization_id, "discovery.schedules")
    resource = await CoreRepository(session).get_resource(
        tenant.organization_id, payload.resource_id, tenant.workspace_id
    )
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    if not resource.enabled:
        raise HTTPException(status_code=409, detail="Resource is disabled")
    binding = await ResourceConnectionRepository(session).get(
        tenant.organization_id, payload.resource_id, tenant.workspace_id
    )
    if binding is None:
        raise HTTPException(status_code=409, detail="Resource has no connector binding")
    next_run = _next_run(payload.cron_expression, payload.timezone)
    schedule = await DiscoveryScheduleRepository(session).create(
        tenant.organization_id,
        tenant.workspace_id,
        payload.resource_id,
        payload.cron_expression,
        payload.timezone,
        next_run,
    )
    await session.commit()
    return _dto(schedule)


@router.patch("/{schedule_id}", response_model=DiscoveryScheduleDTO)
async def update_schedule(
    schedule_id: UUID,
    payload: DiscoveryScheduleUpdateDTO,
    tenant: TenantContext = Depends(require_permissions("discovery.manage")),
    session: AsyncSession = Depends(get_db_session),
) -> DiscoveryScheduleDTO:
    repo = DiscoveryScheduleRepository(session)
    schedule = await repo.get(tenant.organization_id, schedule_id, tenant.workspace_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    values = payload.model_dump(exclude_unset=True)
    cron_expression = values.get("cron_expression", schedule.cron_expression)
    timezone = values.get("timezone", schedule.timezone)
    for key, value in values.items():
        setattr(schedule, key, value)
    if "enabled" in values:
        schedule.next_run_at = _next_run(cron_expression, timezone) if values["enabled"] else None
    elif ("cron_expression" in values or "timezone" in values) and schedule.enabled:
        schedule.next_run_at = _next_run(cron_expression, timezone)
    await session.commit()
    return _dto(schedule)


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    schedule_id: UUID,
    tenant: TenantContext = Depends(require_permissions("discovery.manage")),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    deleted = await DiscoveryScheduleRepository(session).delete(
        tenant.organization_id, schedule_id, tenant.workspace_id
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Schedule not found")
    await session.commit()
