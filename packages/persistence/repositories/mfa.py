from uuid import UUID

from packages.persistence.models.mfa import MfaModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class MfaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: UUID) -> MfaModel | None:
        return await self._session.scalar(select(MfaModel).where(MfaModel.user_id == user_id))

    async def save(self, model: MfaModel) -> MfaModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def delete(self, model: MfaModel) -> None:
        await self._session.delete(model)
        await self._session.flush()
