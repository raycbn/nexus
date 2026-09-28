import pytest
from packages.platform.jobs import JobEnvelope
from packages.platform.redis_persistent_worker import RedisPersistentWorker


class Queue:
    def __init__(self, envelope):
        self.envelope = envelope
        self.acked = []
        self.dlq = []

    async def claim(self, consumer, block_ms=10):
        return [("1-0", {"job": __import__("json").dumps(self.envelope.to_dict())})]

    async def reclaim_pending(self, consumer):
        return []

    def decode(self, fields):
        return self.envelope

    async def ack(self, message_id):
        self.acked.append(message_id)
        return 1

    async def dead_letter(self, message_id, fields, reason):
        self.dlq.append(reason)
        return "2-0"


class Persistent:
    consumer = "worker-1"

    def __init__(self, terminal):
        self.terminal = terminal
        self.repository = self

    async def process_envelope(self, envelope):
        return False

    async def is_terminal_failure(self, job_id):
        return self.terminal


@pytest.mark.asyncio
async def test_transient_failure_is_not_dead_lettered():
    queue = Queue(JobEnvelope.create("demo", {}, "retry"))
    worker = RedisPersistentWorker(queue, Persistent(False))
    assert await worker.process_once() is False
    assert queue.acked == ["1-0"]
    assert queue.dlq == []
