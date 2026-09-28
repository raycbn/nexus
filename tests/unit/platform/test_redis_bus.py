import json
from unittest.mock import AsyncMock

from packages.platform.redis_bus import PlatformEvent, RedisEventBus


def test_platform_event_serializes_metadata() -> None:
    event = PlatformEvent(event_type="remediation.proposed", payload={"id": "123"})
    data = json.loads(event.to_json())

    assert data["event_type"] == "remediation.proposed"
    assert data["payload"] == {"id": "123"}
    assert data["event_id"]
    assert data["occurred_at"]


def test_event_bus_builds_namespaced_channel() -> None:
    redis = AsyncMock()
    bus = RedisEventBus(redis, prefix="test")

    assert bus.channel("remediation") == "test:events:remediation"


async def test_event_bus_publishes_serialized_event() -> None:
    redis = AsyncMock()
    redis.publish.return_value = 2
    bus = RedisEventBus(redis)
    event = PlatformEvent(event_type="incident.created", payload={"id": "abc"})

    subscribers = await bus.publish("incidents", event)

    assert subscribers == 2
    redis.publish.assert_awaited_once()
    channel, payload = redis.publish.await_args.args
    assert channel == "nexus:events:incidents"
    assert json.loads(payload)["event_type"] == "incident.created"
