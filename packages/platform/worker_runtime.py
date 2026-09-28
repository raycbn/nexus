from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from packages.persistence.database import get_session_factory
from packages.persistence.repositories.job import JobRepository
from packages.platform.durable_queue import DurableJobQueue
from packages.platform.job_dispatcher import JobDispatcher
from packages.platform.jobs import JobEnvelope
from packages.platform.persistent_worker import PersistentJobWorker
from packages.platform.redis_persistent_worker import RedisPersistentWorker

Handler = Callable[[JobEnvelope], Awaitable[bool]]


@dataclass
class WorkerRuntime:
    worker: RedisPersistentWorker
    session: object

    async def process_once(self, block_ms: int = 100) -> bool:
        return await self.worker.process_once(block_ms=block_ms)

    async def pending(self) -> int:
        return await self.worker.pending()

    async def close(self) -> None:
        close = getattr(self.session, "close", None)
        if close is not None:
            result = close()
            if hasattr(result, "__await__"):
                await result


async def build_worker_runtime(
    queue: DurableJobQueue,
    consumer: str,
    scheduled_discovery: Handler,
    autonomous_remediation: Handler,
) -> WorkerRuntime:
    session_factory = get_session_factory()
    session = session_factory()
    repository = JobRepository(session)
    dispatcher = JobDispatcher(scheduled_discovery, autonomous_remediation)
    persistent = PersistentJobWorker(repository, consumer, dispatcher)
    return WorkerRuntime(RedisPersistentWorker(queue, persistent), session)
