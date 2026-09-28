import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from redis.asyncio import Redis


@dataclass(frozen=True)
class PlatformEvent:
    event_type: str
    payload: dict
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_json(self) -> str:
        return json.dumps(
            {
                "event_id": str(self.event_id),
                "event_type": self.event_type,
                "occurred_at": self.occurred_at.isoformat(),
                "payload": self.payload,
            },
            sort_keys=True,
        )


class RedisEventBus:
    def __init__(self, redis: Redis, prefix: str = "nexus") -> None:
        self._redis = redis
        self._prefix = prefix

    def channel(self, topic: str) -> str:
        return f"{self._prefix}:events:{topic}"

    async def publish(self, topic: str, event: PlatformEvent) -> int:
        return await self._redis.publish(self.channel(topic), event.to_json())

    async def ping(self) -> bool:
        return bool(await self._redis.ping())
