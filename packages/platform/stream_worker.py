from dataclasses import dataclass

from packages.persistence.repositories.job import JobRepository
from packages.platform.durable_queue import DurableJobQueue


@dataclass
class StreamWorker:
    queue: DurableJobQueue
    repository: JobRepository
    consumer: str
    handler: object
    max_attempts: int = 3

    async def process_once(self) -> bool:
        rows = await self.queue.claim(self.consumer, block_ms=100)
        if not rows:
            rows = await self.queue.reclaim_pending(self.consumer)
        if not rows:
            return False
        message_id, fields = rows[0]
        envelope = self.queue.decode(fields)
        success = await self.handler.process_envelope(envelope)
        if success:
            await self.queue.ack(message_id)
            return True
        exhausted = await self.repository.attempts_exhausted(
            envelope.job_id, self.max_attempts
        )
        if exhausted:
            await self.queue.dead_letter(message_id, fields, "max attempts")
            await self.queue.ack(message_id)
        return False
