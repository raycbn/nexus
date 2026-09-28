from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from packages.platform.job_dispatcher import JobDispatcher
from packages.platform.jobs import JobEnvelope
from packages.platform.persistent_worker import PersistentJobWorker
from packages.platform.redis_persistent_worker import RedisPersistentWorker


async def test_redis_worker_routes_scheduled_discovery_to_dispatcher() -> None:
    job_id = uuid4()
    envelope = JobEnvelope(
        job_id=job_id,
        job_type="discovery.scheduled",
        payload={"schedule_id": str(uuid4())},
        idempotency_key="scheduled:test",
        created_at=datetime.now(UTC),
        attempt=1,
    )
    queue = AsyncMock()
    queue.claim.return_value = [("1-0", {"job_id": "ignored"})]
    queue.decode = Mock(return_value=envelope)
    repository = AsyncMock()
    repository.claim_by_id.return_value = SimpleNamespace(
        id=job_id,
        job_type=envelope.job_type,
        payload=envelope.payload,
        idempotency_key=envelope.idempotency_key,
        created_at=envelope.created_at,
        attempts=1,
    )
    scheduled = AsyncMock(return_value=True)
    remediation = AsyncMock(return_value=True)
    dispatcher = JobDispatcher(scheduled, remediation)
    persistent = PersistentJobWorker(repository, "test-consumer", dispatcher)
    worker = RedisPersistentWorker(queue, persistent)

    assert await worker.process_once() is True

    scheduled.assert_awaited_once()
    assert scheduled.await_args.args[0].job_type == "discovery.scheduled"
    remediation.assert_not_awaited()
    queue.ack.assert_awaited_once_with("1-0")
