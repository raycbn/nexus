from datetime import UTC, datetime
from uuid import UUID

from packages.persistence.models.email_verification_token import EmailVerificationTokenModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession


class EmailVerificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self, user_id: UUID, token_hash: str, expires_at: datetime
    ) -> EmailVerificationTokenModel:
        await self.invalidate_user_tokens(user_id)
        token = EmailVerificationTokenModel(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            created_at=datetime.now(UTC),
        )
        self.session.add(token)
        await self.session.flush()
        return token

    async def get_active(self, token_hash: str) -> EmailVerificationTokenModel | None:
        result = await self.session.execute(
            select(EmailVerificationTokenModel).where(
                EmailVerificationTokenModel.token_hash == token_hash,
                EmailVerificationTokenModel.used_at.is_(None),
                EmailVerificationTokenModel.expires_at > datetime.now(UTC),
            )
        )
        return result.scalar_one_or_none()

    async def invalidate_user_tokens(self, user_id: UUID) -> None:
        await self.session.execute(
            update(EmailVerificationTokenModel)
            .where(
                EmailVerificationTokenModel.user_id == user_id,
                EmailVerificationTokenModel.used_at.is_(None),
            )
            .values(used_at=datetime.now(UTC))
        )
