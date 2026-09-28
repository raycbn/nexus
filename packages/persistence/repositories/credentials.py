from uuid import UUID, uuid4

from packages.domain.models.credential import Credential
from packages.persistence.models.credential import CredentialModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def _to_domain(model: CredentialModel) -> Credential:
    return Credential(
        id=model.id, organization_id=model.organization_id, workspace_id=model.workspace_id,
        name=model.name, credential_type=model.credential_type, secret_ref=model.secret_ref,
        description=model.description, enabled=model.enabled, metadata=model.labels,
        created_at=model.created_at, updated_at=model.updated_at,
    )


class CredentialRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self, organization_id: UUID, workspace_id: UUID | None) -> list[Credential]:
        stmt = select(CredentialModel).where(CredentialModel.organization_id == organization_id)
        if workspace_id is not None:
            stmt = stmt.where(CredentialModel.workspace_id == workspace_id)
        result = await self._session.execute(stmt.order_by(CredentialModel.name))
        return [_to_domain(item) for item in result.scalars().all()]

    async def get(
        self, organization_id: UUID, credential_id: UUID, workspace_id: UUID | None
    ) -> Credential | None:
        stmt = select(CredentialModel).where(
            CredentialModel.id == credential_id, CredentialModel.organization_id == organization_id
        )
        if workspace_id is not None:
            stmt = stmt.where(CredentialModel.workspace_id == workspace_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_domain(model) if model else None

    async def create(
        self, organization_id: UUID, workspace_id: UUID | None, **values: object
    ) -> Credential:
        model = CredentialModel(
            id=uuid4(), organization_id=organization_id, workspace_id=workspace_id, **values
        )
        self._session.add(model)
        await self._session.flush()
        return _to_domain(model)


