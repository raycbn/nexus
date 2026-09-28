from uuid import uuid4

import pytest
from packages.platform.jobs import JobEnvelope
from packages.platform.redis_persistent_worker import RedisPersistentWorker


class Queue:
    def __init__(self, envelope):
        self.envelope = envelope
        self.acked = []
        self.dlq = []

    async def claim(self, consumer, block_ms=10):
        import json
        return [("1-0", {"job": json.dumps(self.envelope.to_dict())})]

    async def reclaim_pending(self, consumer):
        return []

    def decode(self, fields):
        return self.envelope

    async def ack(self, message_id):
        self.acked.append(message_id)
        return 1

    async def dead_letter(self, message_id, fields, reason):
        self.dlq.append((message_id, reason))
        return "2-0"


class Persistent:
    consumer = "worker-1"

    class Repo:
        async def is_terminal_failure(self, job_id):
            return self.terminal

    def __init__(self):
        self.repository = self.Repo()
        self.repository.terminal = False

    async def process_envelope(self, envelope):
        return envelope.job_id == self.expected


@pytest.mark.asyncio
async def test_redis_worker_acks_only_after_persistent_success():
    envelope = JobEnvelope.create("demo", {}, "idempotent")
    queue = Queue(envelope)
    persistent = Persistent()
    persistent.expected = envelope.job_id
    worker = RedisPersistentWorker(queue, persistent)
    assert await worker.process_once() is True
    assert queue.acked == ["1-0"]
    assert queue.dlq == []


@pytest.mark.asyncio
async def test_redis_worker_dead_letters_failed_job():
    envelope = JobEnvelope.create("demo", {}, str(uuid4()))
    queue = Queue(envelope)
    persistent = Persistent()
    persistent.expected = uuid4()
    persistent.repository.terminal = True
    worker = RedisPersistentWorker(queue, persistent)
    assert await worker.process_once() is False
    assert queue.acked == ["1-0"]
    assert queue.dlq[0][0] == "1-0"
