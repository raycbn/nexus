from unittest.mock import AsyncMock, Mock, patch

import pytest
from apps.scheduled_discovery_worker import (
    BATCH_LIMIT,
    SCHEDULED_GROUP,
    SCHEDULED_STREAM,
    process_cycle,
)


@pytest.mark.asyncio
async def test_process_cycle_uses_dedicated_scheduled_queue():
    session = AsyncMock()
    context = AsyncMock()
    context.__aenter__ = AsyncMock(return_value=session)
    context.__aexit__ = AsyncMock(return_value=False)
    session_factory = Mock(return_value=context)
    queue = AsyncMock()
    with (
        patch("apps.scheduled_discovery_worker.DiscoveryScheduler") as scheduler,
        patch("apps.scheduled_discovery_worker.JobRepository"),
        patch("apps.scheduled_discovery_worker.ScheduledDiscoveryHandler"),
        patch("apps.scheduled_discovery_worker.PersistentJobWorker"),
        patch("apps.scheduled_discovery_worker.RedisPersistentWorker") as worker,
    ):
        scheduler.return_value.enqueue_due = AsyncMock(return_value=2)
        worker.return_value.process_once = AsyncMock(return_value=True)
        result = await process_cycle(session_factory, queue)

    assert result == (2, True)
    scheduler.return_value.enqueue_due.assert_awaited_once_with(limit=BATCH_LIMIT)
    worker.return_value.process_once.assert_awaited_once_with(block_ms=100)


def test_scheduled_queue_identity_is_isolated():
    assert SCHEDULED_STREAM == "nexus:scheduled-jobs"
    assert SCHEDULED_GROUP == "nexus-scheduled-workers"
