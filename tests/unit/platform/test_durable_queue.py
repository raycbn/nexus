import json
from uuid import UUID

import pytest
from packages.platform.durable_queue import DurableJobQueue
from packages.platform.jobs import JobEnvelope


class FakeRedis:
    def __init__(self):
        self.rows = []
        self.acked = []
        self.created = False

    async def xgroup_create(self, *args, **kwargs):
        self.created = True

    async def xadd(self, stream, fields):
        self.rows.append(("1-0", fields))
        return "1-0"

    async def xreadgroup(self, *args, **kwargs):
        return [("nexus:jobs", self.rows)] if self.rows else []

    async def xack(self, stream, group, message_id):
        self.acked.append(message_id)
        return 1


@pytest.mark.asyncio
async def test_enqueue_and_claim():
    redis = FakeRedis()
    queue = DurableJobQueue(redis)
    job = JobEnvelope.create("demo", {"x": 1}, "key-1")
    message_id = await queue.enqueue(job)
    rows = await queue.claim("worker-1")
    assert message_id == "1-0"
    assert queue.decode(rows[0][1]) == job
    assert UUID(str(job.job_id))
    assert json.loads(rows[0][1]["job"])["job_type"] == "demo"


@pytest.mark.asyncio
async def test_ack():
    redis = FakeRedis()
    queue = DurableJobQueue(redis)
    assert await queue.ack("1-0") == 1
    assert redis.acked == ["1-0"]


@pytest.mark.asyncio
async def test_reclaim_pending_and_pending_count():
    class PendingRedis(FakeRedis):
        async def xautoclaim(self, *args, **kwargs):
            return ("0-0", self.rows)

        async def xpending(self, *args, **kwargs):
            return {"pending": 2}

    redis = PendingRedis()
    queue = DurableJobQueue(redis)
    job = JobEnvelope.create("demo", {"x": 2}, "key-2")
    await queue.enqueue(job)
    rows = await queue.reclaim_pending("worker-2")
    assert rows[0][0] == "1-0"
    assert await queue.pending_count() == 2


@pytest.mark.asyncio
async def test_dead_letter_preserves_message_and_reason():
    class DLQRedis(FakeRedis):
        async def xadd(self, stream, fields):
            self.dlq = (stream, fields)
            return "2-0"

    redis = DLQRedis()
    queue = DurableJobQueue(redis)
    job = JobEnvelope.create("demo", {"x": 3}, "key-3")
    fields = {"job": json.dumps(job.to_dict())}
    message_id = await queue.dead_letter("1-0", fields, "max attempts")
    assert message_id == "2-0"
    assert redis.dlq[0] == "nexus:jobs:dlq"
    assert redis.dlq[1]["reason"] == "max attempts"
