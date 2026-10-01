from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from croniter import croniter
from sqlalchemy.ext.asyncio import AsyncSession

from packages.persistence.repositories.discovery_schedule import DiscoveryScheduleRepository
from packages.persistence.repositories.job import JobRepository
from packages.platform.durable_queue import DurableJobQueue
from packages.platform.job_service import JobService

DISCOVERY_SCHEDULE_JOB = "discovery.scheduled"


class DiscoveryScheduler:
    def __init__(self, session: AsyncSession, queue: DurableJobQueue) -> None:
        self._session = session
        self._schedules = DiscoveryScheduleRepository(session)
        self._job_service = JobService(JobRepository(session), queue)

    async def enqueue_one_due(self, now: datetime | None = None) -> bool:
        current = now or datetime.now(UTC)
        schedule = await self._schedules.claim_due(current)
        if schedule is None:
            return False
        scheduled_for = schedule.next_run_at
        if scheduled_for is None:
            return False
        next_run = croniter(
            schedule.cron_expression,
            scheduled_for.astimezone(ZoneInfo(schedule.timezone)),
        ).get_next(datetime).astimezone(UTC)
        envelope = await self._job_service.enqueue(
            schedule.organization_id,
            schedule.workspace_id,
            DISCOVERY_SCHEDULE_JOB,
            {
                "schedule_id": str(schedule.id),
                "resource_id": str(schedule.resource_id),
                "organization_id": str(schedule.organization_id),
            },
            f"discovery-schedule:{schedule.id}:{scheduled_for.isoformat()}",
            max_attempts=3,
        )
        schedule.last_run_at = current
        schedule.last_job_id = envelope.job_id
        schedule.next_run_at = next_run
        await self._session.commit()
        return True

    async def enqueue_due(self, now: datetime | None = None, limit: int = 10) -> int:
        if limit < 1:
            return 0
        current = now or datetime.now(UTC)
        count = 0
        while count < limit and await self.enqueue_one_due(current):
            count += 1
        return count
