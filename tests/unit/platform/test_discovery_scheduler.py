from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from packages.platform.discovery_scheduler import (
    DISCOVERY_SCHEDULE_JOB,
    DiscoveryScheduler,
)


@pytest.mark.asyncio
async def test_enqueue_one_due_creates_idempotent_job_and_advances_schedule():
    scheduled_for = datetime(2026, 9, 27, 10, 0, tzinfo=UTC)
    schedule = SimpleNamespace(
        id=uuid4(), organization_id=uuid4(), workspace_id=uuid4(),
        resource_id=uuid4(), cron_expression="*/15 * * * *", timezone="UTC",
        enabled=True, next_run_at=scheduled_for, last_run_at=None, last_job_id=None,
    )
    job = SimpleNamespace(id=uuid4())
    envelope = SimpleNamespace(job_id=job.id)
    session = AsyncMock()
    queue = AsyncMock()
    with (
        patch("packages.platform.discovery_scheduler.DiscoveryScheduleRepository") as schedule_repo,
        patch("packages.platform.discovery_scheduler.JobRepository"),
        patch("packages.platform.discovery_scheduler.JobService") as job_service,
    ):
        schedule_repo.return_value.claim_due = AsyncMock(return_value=schedule)
        job_service.return_value.enqueue = AsyncMock(return_value=envelope)
        result = await DiscoveryScheduler(session, queue).enqueue_one_due(scheduled_for)

    assert result is True
    assert job_service.return_value.enqueue.await_args.args[2] == DISCOVERY_SCHEDULE_JOB
    assert (
        job_service.return_value.enqueue.await_args.args[3]["organization_id"]
        == str(schedule.organization_id)
    )
    assert schedule.last_job_id == job.id
    assert schedule.next_run_at == datetime(2026, 9, 27, 10, 15, tzinfo=UTC)
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_enqueue_one_due_returns_false_when_nothing_is_due():
    session = AsyncMock()
    queue = AsyncMock()
    with patch(
        "packages.platform.discovery_scheduler.DiscoveryScheduleRepository"
    ) as schedule_repo:
        schedule_repo.return_value.claim_due = AsyncMock(return_value=None)
        assert await DiscoveryScheduler(session, queue).enqueue_one_due() is False


@pytest.mark.asyncio
async def test_enqueue_due_honors_limit_and_stops_when_empty():
    session = AsyncMock()
    queue = AsyncMock()
    scheduler = DiscoveryScheduler(session, queue)
    with patch.object(scheduler, "enqueue_one_due", new_callable=AsyncMock) as enqueue:
        enqueue.side_effect = [True, True, False]
        result = await scheduler.enqueue_due(
            datetime(2026, 9, 27, 10, 0, tzinfo=UTC), limit=5
        )

    assert result == 2
    assert enqueue.await_count == 3


@pytest.mark.asyncio
async def test_enqueue_due_rejects_non_positive_limit():
    session = AsyncMock()
    queue = AsyncMock()
    scheduler = DiscoveryScheduler(session, queue)
    assert await scheduler.enqueue_due(limit=0) == 0
