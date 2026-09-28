from datetime import UTC, datetime, timedelta
from uuid import UUID

from packages.persistence.models.job import JobModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class JobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, organization_id: UUID, workspace_id: UUID | None,
        job_type: str, payload: dict, idempotency_key: str, max_attempts: int = 1,
    ) -> JobModel:
        existing = await self.get_by_idempotency(organization_id, workspace_id, idempotency_key)
        if existing is not None:
            return existing
        now = datetime.now(UTC)
        job = JobModel(
            organization_id=organization_id, workspace_id=workspace_id,
            job_type=job_type, payload=payload, idempotency_key=idempotency_key,
            status="queued", max_attempts=max_attempts, available_at=now,
            created_at=now, updated_at=now,
        )
        self._session.add(job)
        await self._session.flush()
        return job

    async def get_by_idempotency(
        self, organization_id: UUID, workspace_id: UUID | None, key: str
    ) -> JobModel | None:
        stmt = select(JobModel).where(
            JobModel.organization_id == organization_id,
            JobModel.workspace_id == workspace_id,
            JobModel.idempotency_key == key,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def claim(self, consumer: str, job_type: str | None = None) -> JobModel | None:
        stmt = select(JobModel).where(
            JobModel.status == "queued", JobModel.available_at <= datetime.now(UTC)
        )
        if job_type is not None:
            stmt = stmt.where(JobModel.job_type == job_type)
        stmt = stmt.order_by(JobModel.created_at.asc()).with_for_update(skip_locked=True).limit(1)
        job = (await self._session.execute(stmt)).scalar_one_or_none()
        if job is None:
            return None
        job.status = "running"
        job.attempts += 1
        job.locked_at = datetime.now(UTC)
        job.locked_by = consumer
        await self._session.flush()
        return job

    async def complete(self, job_id: UUID, result: dict | None = None) -> JobModel | None:
        job = await self._get(job_id)
        if job is None:
            return None
        job.status, job.result = "completed", result or {}
        job.locked_at, job.locked_by = None, None
        await self._session.flush()
        return job

    async def mark_error(self, job_id: UUID, error: str) -> JobModel | None:
        job = await self._get(job_id)
        if job is None:
            return None
        job.error = error
        job.locked_at, job.locked_by = None, None
        job.status = "queued" if job.attempts < job.max_attempts else "failed"
        job.available_at = datetime.now(UTC) + timedelta(seconds=min(60, 2 ** job.attempts))
        await self._session.flush()
        return job

    async def commit(self) -> None:
        await self._session.commit()

    async def _get(self, job_id: UUID) -> JobModel | None:
        result = await self._session.execute(select(JobModel).where(JobModel.id == job_id))
        return result.scalar_one_or_none()

    async def requeue_stale(self, timeout_seconds: int) -> int:
        cutoff = datetime.now(UTC) - timedelta(seconds=timeout_seconds)
        result = await self._session.execute(
            select(JobModel).where(JobModel.status == "running", JobModel.locked_at < cutoff)
        )
        count = 0
        for job in result.scalars().all():
            job.status = "queued" if job.attempts < job.max_attempts else "failed"
            job.locked_at, job.locked_by = None, None
            count += 1
        await self._session.flush()
        return count

    async def claim_by_id(self, job_id: UUID, consumer: str) -> JobModel | None:
        stmt = (
            select(JobModel)
            .where(JobModel.id == job_id, JobModel.status == "queued")
            .with_for_update(skip_locked=True)
        )
        result = await self._session.execute(stmt)
        job = result.scalar_one_or_none()
        if job is None:
            return None
        job.status = "running"
        job.attempts += 1
        job.locked_at = datetime.now(UTC)
        job.locked_by = consumer
        await self._session.flush()
        return job

    async def attempts_exhausted(self, job_id: UUID, max_attempts: int) -> bool:
        job = await self._get(job_id)
        return job is None or job.attempts >= max_attempts

    async def get_for_tenant(
        self, job_id: UUID, organization_id: UUID, workspace_id: UUID | None
    ) -> JobModel | None:
        stmt = select(JobModel).where(
            JobModel.id == job_id,
            JobModel.organization_id == organization_id,
            JobModel.workspace_id == workspace_id,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def status_for(self, job_id: UUID) -> str | None:
        job = await self._get(job_id)
        return job.status if job is not None else None

    async def is_terminal_failure(self, job_id: UUID) -> bool:
        return await self.status_for(job_id) == "failed"
