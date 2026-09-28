from datetime import UTC, datetime
from uuid import UUID, uuid4

from packages.persistence.models.discovery import DiscoveryRunModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class DiscoveryRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        organization_id: UUID,
        workspace_id: UUID | None,
        resource_id: UUID,
        connector_key: str,
    ) -> DiscoveryRunModel:
        model = DiscoveryRunModel(
            id=uuid4(),
            organization_id=organization_id,
            workspace_id=workspace_id,
            resource_id=resource_id,
            connector_key=connector_key,
            status="running",
            started_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        self._session.add(model)
        await self._session.flush()
        return model

    async def complete(
        self,
        model: DiscoveryRunModel,
        *,
        status: str,
        snapshot: list[dict[str, object]],
        imported_count: int = 0,
    ) -> DiscoveryRunModel:
        model.status = status
        model.snapshot = snapshot
        model.discovered_count = len(snapshot)
        model.imported_count = imported_count
        model.completed_at = datetime.now(UTC)
        await self._session.flush()
        return model

    async def get_latest_completed(
        self,
        organization_id: UUID,
        resource_id: UUID,
        workspace_id: UUID | None,
    ) -> DiscoveryRunModel | None:
        runs = await self.list_for_resource(organization_id, resource_id, workspace_id)
        return next((run for run in runs if run.status == "completed"), None)

    async def list_for_resource(
        self,
        organization_id: UUID,
        resource_id: UUID,
        workspace_id: UUID | None,
    ) -> list[DiscoveryRunModel]:
        stmt = select(DiscoveryRunModel).where(
            DiscoveryRunModel.organization_id == organization_id,
            DiscoveryRunModel.resource_id == resource_id,
        )
        if workspace_id is not None:
            stmt = stmt.where(DiscoveryRunModel.workspace_id == workspace_id)
        result = await self._session.execute(
            stmt.order_by(DiscoveryRunModel.started_at.desc())
        )
        return list(result.scalars().all())
