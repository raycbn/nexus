from datetime import UTC, datetime
from uuid import UUID

from packages.persistence.models.api_key import ApiKeyModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class ApiKeyRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_for_organization(self, organization_id: UUID) -> list[ApiKeyModel]:
        result = await self.session.execute(
            select(ApiKeyModel)
            .where(ApiKeyModel.organization_id == organization_id)
            .order_by(ApiKeyModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_hash(self, key_hash: str) -> ApiKeyModel | None:
        result = await self.session.execute(
            select(ApiKeyModel).where(ApiKeyModel.key_hash == key_hash)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        organization_id: UUID,
        user_id: UUID,
        name: str,
        prefix: str,
        key_hash: str,
        scopes: list[str],
        expires_at: datetime | None,
    ) -> ApiKeyModel:
        record = ApiKeyModel(
            organization_id=organization_id,
            created_by_user_id=user_id,
            name=name,
            key_prefix=prefix,
            key_hash=key_hash,
            scopes=scopes,
            expires_at=expires_at,
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def revoke(self, record: ApiKeyModel) -> None:
        record.enabled = False
        await self.session.flush()

    async def mark_used(self, record: ApiKeyModel) -> None:
        record.last_used_at = datetime.now(UTC)
        await self.session.flush()
