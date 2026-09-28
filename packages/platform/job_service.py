from uuid import UUID

from packages.persistence.repositories.job import JobRepository
from packages.platform.durable_queue import DurableJobQueue
from packages.platform.jobs import JobEnvelope


class JobService:
    def __init__(self, repository: JobRepository, queue: DurableJobQueue) -> None:
        self._repository = repository
        self._queue = queue

    async def enqueue(
        self,
        organization_id: UUID,
        workspace_id: UUID | None,
        job_type: str,
        payload: dict,
        idempotency_key: str,
        max_attempts: int = 1,
    ) -> JobEnvelope:
        model = await self._repository.create(
            organization_id, workspace_id, job_type, payload, idempotency_key, max_attempts
        )
        await self._repository.commit()
        envelope = JobEnvelope(
            job_id=model.id,
            job_type=model.job_type,
            payload=model.payload,
            idempotency_key=model.idempotency_key,
            created_at=model.created_at,
            attempt=model.attempts,
        )
        await self._queue.enqueue(envelope)
        return envelope

    async def enqueue_autonomous_remediation(self, job) -> JobEnvelope:
        from packages.platform.job_types import AUTONOMOUS_REMEDIATION

        return await self.enqueue(
            job.organization_id,
            job.workspace_id,
            AUTONOMOUS_REMEDIATION,
            job.to_payload(),
            f"autonomous-remediation:{job.action_id}",
            max_attempts=3,
        )
