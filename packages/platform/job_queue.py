import json
from dataclasses import dataclass

from packages.platform.jobs import JobEnvelope
from packages.platform.redis_bus import RedisEventBus


@dataclass(frozen=True)
class JobQueue:
    bus: RedisEventBus
    topic: str = "jobs"

    async def enqueue(self, job: JobEnvelope) -> int:
        return await self.bus.publish(
            self.topic,
            event=self._event(job),
        )

    @staticmethod
    def _event(job: JobEnvelope):
        from packages.platform.redis_bus import PlatformEvent

        return PlatformEvent(event_type="job.enqueued", payload=job.to_dict())

    @staticmethod
    def decode(message: str) -> JobEnvelope:
        return JobEnvelope.from_dict(json.loads(message))
