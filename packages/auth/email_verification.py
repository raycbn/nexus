import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from packages.persistence.repositories.email_verification import EmailVerificationRepository

TOKEN_TTL = timedelta(hours=24)


def hash_verification_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def issue_email_verification(
    repository: EmailVerificationRepository, user_id: UUID
) -> str:
    token = secrets.token_urlsafe(32)
    await repository.create(
        user_id,
        hash_verification_token(token),
        datetime.now(UTC) + TOKEN_TTL,
    )
    return token
