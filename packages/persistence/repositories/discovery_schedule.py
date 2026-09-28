from datetime import UTC, datetime
from uuid import UUID, uuid4

from packages.persistence.models.discovery_schedule import DiscoveryScheduleModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class DiscoveryScheduleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        organization_id: UUID,
        workspace_id: UUID | None,
        resource_id: UUID,
        cron_expression: str,
        timezone: str,
        next_run_at: datetime | None,
    ) -> DiscoveryScheduleModel:
        now = datetime.now(UTC)
        schedule = DiscoveryScheduleModel(
            id=uuid4(),
            organization_id=organization_id,
            workspace_id=workspace_id,
            resource_id=resource_id,
            cron_expression=cron_expression,
            timezone=timezone,
            enabled=True,
            next_run_at=next_run_at,
            created_at=now,
            updated_at=now,
        )
        self._session.add(schedule)
        await self._session.flush()
        return schedule

    async def list_for_workspace(
        self, organization_id: UUID, workspace_id: UUID | None
    ) -> list[DiscoveryScheduleModel]:
        stmt = select(DiscoveryScheduleModel).where(
            DiscoveryScheduleModel.organization_id == organization_id,
        )
        if workspace_id is not None:
            stmt = stmt.where(DiscoveryScheduleModel.workspace_id == workspace_id)
        result = await self._session.execute(
            stmt.order_by(DiscoveryScheduleModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def claim_due(self, now: datetime) -> DiscoveryScheduleModel | None:
        stmt = (
            select(DiscoveryScheduleModel)
            .where(
                DiscoveryScheduleModel.enabled.is_(True),
                DiscoveryScheduleModel.next_run_at.is_not(None),
                DiscoveryScheduleModel.next_run_at <= now,
            )
            .order_by(DiscoveryScheduleModel.next_run_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        schedule = (await self._session.execute(stmt)).scalar_one_or_none()
        return schedule

    async def get_by_id(self, schedule_id: UUID) -> DiscoveryScheduleModel | None:
        stmt = select(DiscoveryScheduleModel).where(DiscoveryScheduleModel.id == schedule_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get(
        self, organization_id: UUID, schedule_id: UUID, workspace_id: UUID | None
    ) -> DiscoveryScheduleModel | None:
        stmt = select(DiscoveryScheduleModel).where(
            DiscoveryScheduleModel.id == schedule_id,
            DiscoveryScheduleModel.organization_id == organization_id,
        )
        if workspace_id is not None:
            stmt = stmt.where(DiscoveryScheduleModel.workspace_id == workspace_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()
