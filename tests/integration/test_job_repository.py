from uuid import uuid4

import pytest
from packages.persistence.config import database_settings
from packages.persistence.models.job import JobModel
from packages.persistence.repositories.job import JobRepository
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool


@pytest.fixture(scope="session")
def job_engine():
    engine = create_async_engine(database_settings.database_url, poolclass=NullPool)
    yield engine


@pytest.fixture
async def session_factory(job_engine):
    return async_sessionmaker(job_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.mark.asyncio
async def test_job_repository_persists_idempotent_and_claims(session_factory):
    organization_id = uuid4()
    job_type = f"test.job.{uuid4()}"
    workspace_id = uuid4()
    async with session_factory() as session:
        repo = JobRepository(session)
        first = await repo.create(
            organization_id, workspace_id, job_type, {"value": 1}, "idem-1", max_attempts=2
        )
        second = await repo.create(
            organization_id, workspace_id, job_type, {"value": 2}, "idem-1", max_attempts=2
        )
        assert first.id == second.id
        claimed = await repo.claim("integration-worker", job_type=job_type)
        assert claimed is not None
        assert claimed.attempts == 1
        assert claimed.status == "running"
        await session.commit()

    async with session_factory() as session:
        result = await session.execute(select(JobModel).where(JobModel.id == first.id))
        job = result.scalar_one()
        assert job.locked_by == "integration-worker"
        await session.execute(delete(JobModel).where(JobModel.id == first.id))
        await session.commit()
