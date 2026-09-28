import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from packages.persistence.repositories.password_reset import PasswordResetRepository

TOKEN_TTL = timedelta(minutes=30)


def generate_reset_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(48)
    return raw, hashlib.sha256(raw.encode("utf-8")).hexdigest()


def hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def issue_password_reset(repository: PasswordResetRepository, user_id: UUID) -> str:
    raw, token_hash = generate_reset_token()
    await repository.invalidate_user_tokens(user_id)
    await repository.create(user_id, token_hash, datetime.now(UTC) + TOKEN_TTL)
    return raw
