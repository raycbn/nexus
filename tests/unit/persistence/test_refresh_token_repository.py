from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from packages.persistence.models.refresh_token import RefreshTokenModel
from packages.persistence.repositories.refresh_token import RefreshTokenRepository
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def session() -> AsyncMock:
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def repo(session: AsyncMock) -> RefreshTokenRepository:
    return RefreshTokenRepository(session)


def mock_result(value: RefreshTokenModel | None) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


@pytest.mark.asyncio
async def test_create_persists_refresh_token(repo: RefreshTokenRepository, session: AsyncMock):
    expires_at = datetime.now(UTC) + timedelta(days=7)
    result = await repo.create(uuid4(), "jti-123", expires_at)

    assert result.jti == "jti-123"
    assert result.expires_at == expires_at
    session.add.assert_called_once_with(result)
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_for_update_returns_revoked_token(
    repo: RefreshTokenRepository, session: AsyncMock
):
    token = RefreshTokenModel(
        id=uuid4(),
        user_id=uuid4(),
        jti="revoked-jti",
        expires_at=datetime.now(UTC) + timedelta(days=1),
        revoked_at=datetime.now(UTC),
        replaced_by_jti="new-jti",
    )
    session.execute = AsyncMock(return_value=mock_result(token))

    result = await repo.get_for_update("revoked-jti")

    assert result is token
    statement = session.execute.call_args.args[0]
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert "FOR UPDATE" in sql


@pytest.mark.asyncio
async def test_get_active_returns_only_active_token(
    repo: RefreshTokenRepository, session: AsyncMock
):
    token = RefreshTokenModel(
        id=uuid4(),
        user_id=uuid4(),
        jti="jti-123",
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    session.execute = AsyncMock(return_value=mock_result(token))

    result = await repo.get_active("jti-123")

    assert result is token
    session.execute.assert_awaited_once()
    statement = session.execute.call_args.args[0]
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert "FOR UPDATE" in sql


@pytest.mark.asyncio
async def test_get_active_returns_none_when_not_found(
    repo: RefreshTokenRepository, session: AsyncMock
):
    session.execute = AsyncMock(return_value=mock_result(None))

    result = await repo.get_active("missing")

    assert result is None


@pytest.mark.asyncio
async def test_revoke_marks_token_and_replacement(
    repo: RefreshTokenRepository, session: AsyncMock
):
    token = RefreshTokenModel(
        id=uuid4(),
        user_id=uuid4(),
        jti="old-jti",
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )

    await repo.revoke(token, replaced_by_jti="new-jti")

    assert token.revoked_at is not None
    assert token.replaced_by_jti == "new-jti"
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_revoke_family_revokes_descendants(repo: RefreshTokenRepository, session: AsyncMock):
    first = RefreshTokenModel(
        id=uuid4(), user_id=uuid4(), jti="first", expires_at=datetime.now(UTC) + timedelta(days=1),
        revoked_at=datetime.now(UTC), replaced_by_jti="second",
    )
    second = RefreshTokenModel(
        id=uuid4(),
        user_id=first.user_id,
        jti="second",
        expires_at=datetime.now(UTC) + timedelta(days=1),
        replaced_by_jti="third",
    )
    third = RefreshTokenModel(
        id=uuid4(),
        user_id=first.user_id,
        jti="third",
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    session.execute = AsyncMock(side_effect=[mock_result(second), mock_result(third)])

    await repo.revoke_family(first)

    assert second.revoked_at is not None
    assert third.revoked_at is not None
    assert session.execute.await_count == 2
