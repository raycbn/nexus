import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from packages.persistence.config import database_settings
from packages.persistence.models.core import OrganizationModel, UserModel
from packages.persistence.models.refresh_token import RefreshTokenModel
from packages.persistence.repositories.refresh_token import RefreshTokenRepository
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool


@pytest.fixture(scope="session")
def test_engine():
    engine = create_async_engine(
        database_settings.database_url,
        echo=False,
        poolclass=NullPool,
    )
    yield engine


@pytest.fixture
async def session_factory(test_engine):
    return async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


@pytest.mark.asyncio
async def test_refresh_token_row_lock_prevents_double_consumption(session_factory):
    org_id = uuid4()
    user_id = uuid4()
    jti = str(uuid4())

    async with session_factory() as setup:
        setup.add(OrganizationModel(id=org_id, name=f"test-{org_id}"))
        setup.add(
            UserModel(
                id=user_id,
                organization_id=org_id,
                email=f"{user_id}@example.test",
                display_name="Concurrency Test",
                password_hash="unused",
                role="member",
            )
        )
        await setup.commit()

        setup.add(
            RefreshTokenModel(
                id=uuid4(),
                user_id=user_id,
                jti=jti,
                expires_at=datetime.now(UTC) + timedelta(minutes=5),
            )
        )
        await setup.commit()

    async with session_factory() as session1, session_factory() as session2:
        repo1 = RefreshTokenRepository(session1)
        repo2 = RefreshTokenRepository(session2)

        acquired = asyncio.Event()
        execute_started = asyncio.Event()
        release = asyncio.Event()

        original_execute = session2.execute

        async def tracked_execute(statement, *args, **kwargs):
            execute_started.set()
            return await original_execute(statement, *args, **kwargs)

        session2.execute = tracked_execute  # type: ignore[method-assign]

        async def first_consumer():
            token = await repo1.get_active(jti)
            assert token is not None
            acquired.set()
            await release.wait()
            await repo1.revoke(token, replaced_by_jti="replacement-jti")
            await session1.commit()

        first_task = asyncio.create_task(first_consumer())
        await acquired.wait()

        second_task = asyncio.create_task(repo2.get_active(jti))
        await execute_started.wait()

        release.set()
        second_result = await second_task
        await first_task

        assert second_result is None

    async with session_factory() as cleanup:
        result = await cleanup.get(UserModel, user_id)
        if result is not None:
            await cleanup.delete(result)
            await cleanup.commit()
