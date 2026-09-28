from datetime import UTC, datetime
from uuid import UUID, uuid4

from packages.persistence.models.refresh_token import RefreshTokenModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, user_id: UUID, jti: str, expires_at: datetime,
        user_agent: str | None = None, ip_address: str | None = None,
    ) -> RefreshTokenModel:
        token = RefreshTokenModel(
            id=uuid4(), user_id=user_id, jti=jti, expires_at=expires_at,
            user_agent=user_agent, ip_address=ip_address,
        )
        self._session.add(token)
        await self._session.flush()
        return token

    async def get_for_update(self, jti: str) -> RefreshTokenModel | None:
        stmt = select(RefreshTokenModel).where(RefreshTokenModel.jti == jti).with_for_update()
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active(self, jti: str) -> RefreshTokenModel | None:
        stmt = select(RefreshTokenModel).where(
            RefreshTokenModel.jti == jti,
            RefreshTokenModel.revoked_at.is_(None),
            RefreshTokenModel.expires_at > datetime.now(UTC),
        ).with_for_update()
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: UUID) -> list[RefreshTokenModel]:
        result = await self._session.execute(
            select(RefreshTokenModel)
            .where(RefreshTokenModel.user_id == user_id)
            .order_by(RefreshTokenModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def revoke(self, token: RefreshTokenModel, replaced_by_jti: str | None = None) -> None:
        token.revoked_at = datetime.now(UTC)
        token.replaced_by_jti = replaced_by_jti
        await self._session.flush()

    async def revoke_for_user(self, user_id: UUID, jti: str) -> bool:
        result = await self._session.execute(
            update(RefreshTokenModel)
            .where(RefreshTokenModel.user_id == user_id, RefreshTokenModel.jti == jti,
                   RefreshTokenModel.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
        await self._session.flush()
        return result.rowcount == 1

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        await self._session.execute(
            update(RefreshTokenModel)
            .where(RefreshTokenModel.user_id == user_id, RefreshTokenModel.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
        await self._session.flush()

    async def revoke_family(self, token: RefreshTokenModel) -> None:
        current_jti = token.replaced_by_jti
        visited: set[str] = set()
        while current_jti is not None and current_jti not in visited:
            visited.add(current_jti)
            current = await self.get_for_update(current_jti)
            if current is None:
                break
            if current.revoked_at is None:
                current.revoked_at = datetime.now(UTC)
                await self._session.flush()
            current_jti = current.replaced_by_jti
