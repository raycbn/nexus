from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from packages.persistence.models.job import JobModel
from packages.persistence.repositories.job import JobRepository
from packages.platform.jobs import JobEnvelope

JobHandler = Callable[[JobEnvelope], Awaitable[bool]]


@dataclass
class PersistentJobWorker:
    repository: JobRepository
    consumer: str
    handler: JobHandler

    async def process_once(self) -> bool:
        job = await self.repository.claim(self.consumer)
        if job is None:
            return False
        return await self._run_claimed(job)

    async def process_envelope(self, envelope: JobEnvelope) -> bool:
        job = await self.repository.claim_by_id(envelope.job_id, self.consumer)
        if job is None:
            return False
        return await self._run_claimed(job)

    async def _run_claimed(self, job: JobModel) -> bool:
        envelope = _to_envelope(job)
        try:
            success = await self.handler(envelope)
        except Exception as exc:
            await self.repository.mark_error(job.id, str(exc))
            await self.repository.commit()
            return False
        if success:
            await self.repository.complete(job.id, {"worker": self.consumer})
        else:
            await self.repository.mark_error(job.id, "handler returned failure")
        await self.repository.commit()
        return success

    async def recover_stale(self, timeout_seconds: int = 300) -> int:
        count = await self.repository.requeue_stale(timeout_seconds)
        await self.repository.commit()
        return count


def _to_envelope(job: JobModel) -> JobEnvelope:
    return JobEnvelope(
        job_id=job.id,
        job_type=job.job_type,
        payload=job.payload,
        idempotency_key=job.idempotency_key,
        created_at=job.created_at,
        attempt=job.attempts,
    )
