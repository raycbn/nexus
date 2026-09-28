from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from packages.platform.job_types import DISCOVERY_SCHEDULE_JOB
from packages.platform.jobs import JobEnvelope

Handler = Callable[[JobEnvelope], Awaitable[bool]]


@dataclass
class JobDispatcher:
    """Route durable jobs to their typed handlers."""

    scheduled_discovery: Handler
    autonomous_remediation: Handler

    async def __call__(self, envelope: JobEnvelope) -> bool:
        if envelope.job_type == DISCOVERY_SCHEDULE_JOB:
            return await self.scheduled_discovery(envelope)
        if envelope.job_type == "remediation.autonomous":
            return await self.autonomous_remediation(envelope)
        return False
