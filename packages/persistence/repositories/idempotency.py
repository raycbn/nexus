from uuid import UUID

from packages.persistence.models.idempotency import IdempotencyKeyModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class IdempotencyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, organization_id: UUID, key: str) -> IdempotencyKeyModel | None:
        result = await self.session.execute(
            select(IdempotencyKeyModel).where(
                IdempotencyKeyModel.organization_id == organization_id,
                IdempotencyKeyModel.key == key,
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        organization_id: UUID,
        key: str,
        request_hash: str,
        response: dict,
    ) -> IdempotencyKeyModel:
        model = IdempotencyKeyModel(
            organization_id=organization_id,
            key=key,
            request_hash=request_hash,
            response=response,
        )
        self.session.add(model)
        await self.session.flush()
        return model
