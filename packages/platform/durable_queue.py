import json
from dataclasses import dataclass

from redis.asyncio import Redis

from packages.platform.jobs import JobEnvelope


@dataclass(frozen=True)
class DurableJobQueue:
    redis: Redis
    stream: str = "nexus:jobs"
    group: str = "nexus-workers"

    async def ensure_group(self) -> None:
        try:
            await self.redis.xgroup_create(
                self.stream, self.group, id="0", mkstream=True
            )
        except Exception as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    async def enqueue(self, job: JobEnvelope) -> str:
        payload = json.dumps(job.to_dict(), sort_keys=True)
        return await self.redis.xadd(self.stream, {"job": payload})

    async def claim(self, consumer: str, block_ms: int = 1000):
        await self.ensure_group()
        rows = await self.redis.xreadgroup(
            self.group, consumer, {self.stream: ">"}, count=1, block=block_ms
        )
        return rows[0][1] if rows else []

    async def ack(self, message_id: str) -> int:
        return await self.redis.xack(self.stream, self.group, message_id)

    @staticmethod
    def decode(fields: dict) -> JobEnvelope:
        return JobEnvelope.from_dict(json.loads(fields["job"]))


    async def reclaim_pending(self, consumer: str, min_idle_ms: int = 30_000, count: int = 10):
        await self.ensure_group()
        rows = await self.redis.xautoclaim(
            self.stream, self.group, consumer, min_idle_ms, start_id="0-0", count=count
        )
        return rows[1] if len(rows) > 1 else []

    async def pending_count(self) -> int:
        await self.ensure_group()
        info = await self.redis.xpending(self.stream, self.group)
        return int(info.get("pending", 0)) if isinstance(info, dict) else int(info[0])

    async def dead_letter(self, message_id: str, fields: dict, reason: str) -> str:
        return await self.redis.xadd(
            f"{self.stream}:dlq",
            {"message_id": message_id, "reason": reason, "job": fields.get("job", "")},
        )
