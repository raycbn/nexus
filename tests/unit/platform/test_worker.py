import pytest
from packages.platform.jobs import JobEnvelope
from packages.platform.worker import JobWorker


class FakeQueue:
    def __init__(self, success=True):
        self.success = success
        self.acked = []
        self.job = JobEnvelope.create("demo", {}, "worker-key")

    async def claim(self, consumer, block_ms=1000):
        return [("1-0", {"job": __import__("json").dumps(self.job.to_dict())})]

    def decode(self, fields):
        return self.job

    async def ack(self, message_id):
        self.acked.append(message_id)
        return 1


@pytest.mark.asyncio
async def test_worker_acks_successful_job():
    queue = FakeQueue()
    seen = []

    async def handler(job):
        seen.append(job.job_id)
        return True

    assert await JobWorker(queue, "w1", handler).process_once()
    assert seen == [queue.job.job_id]
    assert queue.acked == ["1-0"]


@pytest.mark.asyncio
async def test_worker_does_not_ack_failed_job():
    queue = FakeQueue()

    async def handler(job):
        return False

    assert not await JobWorker(queue, "w1", handler).process_once()
    assert queue.acked == []
