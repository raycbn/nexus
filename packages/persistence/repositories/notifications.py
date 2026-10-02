from uuid import UUID

from packages.persistence.models.notification import (
    NotificationDeliveryModel,
    NotificationEndpointModel,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class NotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_endpoints(self, organization_id: UUID, workspace_id: UUID | None):
        stmt = select(NotificationEndpointModel).where(
            NotificationEndpointModel.organization_id == organization_id
        )
        if workspace_id is not None:
            stmt = stmt.where(NotificationEndpointModel.workspace_id == workspace_id)
        return list(
            (await self.session.scalars(stmt.order_by(NotificationEndpointModel.name))).all()
        )

    async def get_endpoint(
        self, organization_id: UUID, endpoint_id: UUID, workspace_id: UUID | None
    ):
        stmt = select(NotificationEndpointModel).where(
            NotificationEndpointModel.id == endpoint_id,
            NotificationEndpointModel.organization_id == organization_id,
        )
        if workspace_id is not None:
            stmt = stmt.where(NotificationEndpointModel.workspace_id == workspace_id)
        return await self.session.scalar(stmt)

    async def deliveries(self, endpoint_id: UUID, limit: int = 50):
        stmt = (
            select(NotificationDeliveryModel)
            .where(NotificationDeliveryModel.endpoint_id == endpoint_id)
            .order_by(NotificationDeliveryModel.created_at.desc())
            .limit(limit)
        )
        return list((await self.session.scalars(stmt)).all())
