from datetime import UTC, datetime
from uuid import UUID

from packages.persistence.models.usage import UsageEventModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


class UsageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record(
        self,
        organization_id: UUID,
        workspace_id: UUID | None,
        metric: str,
        quantity: float,
        source: str,
        dimensions: dict[str, str],
        occurred_at: datetime | None,
    ) -> UsageEventModel:
        event = UsageEventModel(
            organization_id=organization_id,
            workspace_id=workspace_id,
            metric=metric,
            quantity=quantity,
            source=source,
            dimensions=dimensions,
            occurred_at=occurred_at or datetime.now(UTC),
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def summary(
        self,
        organization_id: UUID,
        workspace_id: UUID | None,
        start: datetime,
        end: datetime,
    ) -> list[tuple[str, float]]:
        stmt = select(UsageEventModel.metric, func.sum(UsageEventModel.quantity)).where(
            UsageEventModel.organization_id == organization_id,
            UsageEventModel.occurred_at >= start,
            UsageEventModel.occurred_at < end,
        )
        if workspace_id is not None:
            stmt = stmt.where(UsageEventModel.workspace_id == workspace_id)
        stmt = stmt.group_by(UsageEventModel.metric).order_by(UsageEventModel.metric)
        rows = (await self.session.execute(stmt)).all()
        return [(metric, float(total)) for metric, total in rows]

    async def list_events(
        self,
        organization_id: UUID,
        workspace_id: UUID | None,
        limit: int,
    ) -> list[UsageEventModel]:
        stmt = select(UsageEventModel).where(UsageEventModel.organization_id == organization_id)
        if workspace_id is not None:
            stmt = stmt.where(UsageEventModel.workspace_id == workspace_id)
        stmt = stmt.order_by(UsageEventModel.occurred_at.desc()).limit(limit)
        return list((await self.session.scalars(stmt)).all())
