from dataclasses import dataclass

from packages.platform.durable_queue import DurableJobQueue
from packages.platform.persistent_worker import PersistentJobWorker


@dataclass
class RedisPersistentWorker:
    queue: DurableJobQueue
    persistent: PersistentJobWorker
    max_pending_attempts: int = 3

    async def process_once(self, block_ms: int = 10) -> bool:
        messages = await self.queue.claim(self.persistent.consumer, block_ms=block_ms)
        if not messages:
            messages = await self.queue.reclaim_pending(self.persistent.consumer)
        if not messages:
            return False
        message_id, fields = messages[0]
        envelope = self.queue.decode(fields)
        success = await self.persistent.process_envelope(envelope)
        if success:
            await self.queue.ack(message_id)
            return True
        terminal = await self.persistent.repository.is_terminal_failure(envelope.job_id)
        if terminal and hasattr(self.queue, "dead_letter"):
            await self.queue.dead_letter(
                message_id, fields, "persistent job attempts exhausted"
            )
        await self.queue.ack(message_id)
        return False

    async def pending(self) -> int:
        return await self.queue.pending_count()
