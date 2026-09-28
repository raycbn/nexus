from uuid import uuid4

import pytest
from packages.platform.job_types import AutonomousRemediationJob
from packages.platform.jobs import JobEnvelope
from packages.remediation.autonomous_worker import AutonomousRemediationWorker


@pytest.mark.asyncio
async def test_worker_rejects_incomplete_job_payload():
    worker = AutonomousRemediationWorker(lambda job: None)
    envelope = JobEnvelope.create("remediation.autonomous", {"action_id": str(uuid4())}, "bad")
    with pytest.raises(ValueError):
        await worker.handle(envelope)


@pytest.mark.asyncio
async def test_worker_requires_expected_context_shape(monkeypatch):
    job = AutonomousRemediationJob(
        uuid4(), uuid4(), None, uuid4(), uuid4(), uuid4()
    )
    seen = []

    async def loader(value):
        seen.append(value)
        return {}

    async def fake_execute(**context):
        assert context == {}
        return type("Result", (), {"loop": type("Loop", (), {"decision": "verified"})()})()

    monkeypatch.setattr(
        "packages.remediation.autonomous_worker.execute_autonomous_remediation", fake_execute
    )
    envelope = JobEnvelope.create("remediation.autonomous", job.to_payload(), "job")
    assert await AutonomousRemediationWorker(loader).handle(envelope) is True
    assert seen == [job]
