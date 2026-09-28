from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from packages.platform.durable_queue import DurableJobQueue
from packages.platform.jobs import JobEnvelope

JobHandler = Callable[[JobEnvelope], Awaitable[bool]]


@dataclass
class JobWorker:
    queue: DurableJobQueue
    consumer: str
    handler: JobHandler

    async def process_once(self) -> bool:
        messages = await self.queue.claim(self.consumer, block_ms=10)
        if not messages:
            return False
        message_id, fields = messages[0]
        job = self.queue.decode(fields)
        success = await self.handler(job)
        if success:
            await self.queue.ack(message_id)
        return success
