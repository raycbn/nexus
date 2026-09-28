import pytest
from packages.platform.jobs import JobEnvelope
from packages.platform.stream_worker import StreamWorker


class Queue:
    def __init__(self, job):
        self.job = job
        self.acked = []
        self.dlq = []

    async def claim(self, consumer, block_ms=100):
        return [("1-0", {"job": self.job.to_dict()})]

    async def reclaim_pending(self, consumer):
        return []

    def decode(self, fields):
        return JobEnvelope.from_dict(fields["job"])

    async def ack(self, message_id):
        self.acked.append(message_id)
        return 1

    async def dead_letter(self, message_id, fields, reason):
        self.dlq.append((message_id, reason))
        return "2-0"


class Repo:
    def __init__(self, exhausted):
        self.exhausted = exhausted

    async def attempts_exhausted(self, job_id, max_attempts):
        return self.exhausted


class Handler:
    async def process_envelope(self, envelope):
        return False


@pytest.mark.asyncio
async def test_failed_job_is_retried_without_ack_when_not_exhausted():
    queue = Queue(JobEnvelope.create("demo", {}, "retry"))
    worker = StreamWorker(queue, Repo(False), "w1", Handler())
    assert await worker.process_once() is False
    assert queue.acked == []
    assert queue.dlq == []


@pytest.mark.asyncio
async def test_exhausted_job_moves_to_dlq_and_is_acked():
    queue = Queue(JobEnvelope.create("demo", {}, "dead"))
    worker = StreamWorker(queue, Repo(True), "w1", Handler())
    assert await worker.process_once() is False
    assert queue.acked == ["1-0"]
    assert queue.dlq == [("1-0", "max attempts")]
