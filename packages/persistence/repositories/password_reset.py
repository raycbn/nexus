from datetime import UTC, datetime
from uuid import UUID

from packages.persistence.models.password_reset_token import PasswordResetTokenModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession


class PasswordResetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self, user_id: UUID, token_hash: str, expires_at: datetime
    ) -> PasswordResetTokenModel:
        token = PasswordResetTokenModel(
            user_id=user_id, token_hash=token_hash, expires_at=expires_at
        )
        self.session.add(token)
        await self.session.flush()
        return token

    async def get_active(self, token_hash: str) -> PasswordResetTokenModel | None:
        result = await self.session.execute(
            select(PasswordResetTokenModel).where(
                PasswordResetTokenModel.token_hash == token_hash,
                PasswordResetTokenModel.used_at.is_(None),
                PasswordResetTokenModel.expires_at > datetime.now(UTC),
            )
        )
        return result.scalar_one_or_none()

    async def consume(self, token: PasswordResetTokenModel) -> None:
        token.used_at = datetime.now(UTC)

    async def invalidate_user_tokens(self, user_id: UUID) -> None:
        await self.session.execute(
            update(PasswordResetTokenModel)
            .where(
                PasswordResetTokenModel.user_id == user_id,
                PasswordResetTokenModel.used_at.is_(None),
            )
            .values(used_at=datetime.now(UTC))
        )
