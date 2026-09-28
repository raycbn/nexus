from uuid import UUID, uuid4

from packages.persistence.models.resource_connection import ResourceConnectionModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class ResourceConnectionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, organization_id: UUID, resource_id: UUID, workspace_id: UUID | None):
        stmt = select(ResourceConnectionModel).where(
            ResourceConnectionModel.organization_id == organization_id,
            ResourceConnectionModel.resource_id == resource_id,
        )
        if workspace_id is not None:
            stmt = stmt.where(ResourceConnectionModel.workspace_id == workspace_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(
        self,
        organization_id: UUID,
        workspace_id: UUID | None,
        resource_id: UUID,
        connector_key: str,
        credential_id: UUID,
        config: dict[str, str],
    ) -> ResourceConnectionModel:
        model = await self.get(organization_id, resource_id, workspace_id)
        if model is None:
            model = ResourceConnectionModel(
                id=uuid4(),
                organization_id=organization_id,
                workspace_id=workspace_id,
                resource_id=resource_id,
                connector_key=connector_key,
                credential_id=credential_id,
                config=config,
            )
            self._session.add(model)
        else:
            model.connector_key = connector_key
            model.credential_id = credential_id
            model.config = config
        await self._session.flush()
        return model
