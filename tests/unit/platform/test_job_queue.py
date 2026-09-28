import json
from uuid import UUID

import pytest
from packages.platform.job_queue import JobQueue
from packages.platform.jobs import JobEnvelope


class FakeBus:
    async def publish(self, topic, event):
        return 1


@pytest.mark.asyncio
async def test_enqueue_publishes_job_event(monkeypatch):
    calls = []

    async def fake_publish(self, topic, event):
        calls.append((topic, event))
        return 1

    monkeypatch.setattr(FakeBus, "publish", fake_publish)
    queue = JobQueue(FakeBus())
    job = JobEnvelope.create("test", {"a": 1}, "id-1")

    assert await queue.enqueue(job) == 1
    assert calls[0][0] == "jobs"
    assert calls[0][1].event_type == "job.enqueued"
    assert UUID(calls[0][1].payload["job_id"])


def test_decode_event_payload():
    job = JobEnvelope.create("test", {"a": 1}, "id-2")
    assert JobQueue.decode(json.dumps(job.to_dict())) == job
