import asyncio

from packages.domain.config import NexusSettings
from packages.persistence.database import get_session_factory
from packages.persistence.repositories.job import JobRepository
from packages.platform.discovery_scheduler import DiscoveryScheduler
from packages.platform.durable_queue import DurableJobQueue
from packages.platform.persistent_worker import PersistentJobWorker
from packages.platform.redis_persistent_worker import RedisPersistentWorker
from packages.platform.scheduled_discovery_handler import ScheduledDiscoveryHandler
from redis.asyncio import Redis

SCHEDULED_STREAM = "nexus:scheduled-jobs"
SCHEDULED_GROUP = "nexus-scheduled-workers"
POLL_INTERVAL_SECONDS = 5
BATCH_LIMIT = 10


async def process_cycle(session_factory, queue: DurableJobQueue) -> tuple[int, bool]:
    async with session_factory() as session:
        scheduler = DiscoveryScheduler(session, queue)
        enqueued = await scheduler.enqueue_due(limit=BATCH_LIMIT)
        repository = JobRepository(session)
        handler = ScheduledDiscoveryHandler(session)
        persistent = PersistentJobWorker(repository, "scheduled-discovery-worker", handler)
        worker = RedisPersistentWorker(queue, persistent)
        processed = await worker.process_once(block_ms=100)
    return enqueued, processed


async def run() -> None:
    settings = NexusSettings()
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    queue = DurableJobQueue(redis, stream=SCHEDULED_STREAM, group=SCHEDULED_GROUP)
    await queue.ensure_group()
    session_factory = get_session_factory()
    try:
        while True:
            await process_cycle(session_factory, queue)
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
    finally:
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(run())
