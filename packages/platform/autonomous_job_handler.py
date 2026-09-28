from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from packages.platform.job_types import AUTONOMOUS_REMEDIATION, AutonomousRemediationJob
from packages.platform.jobs import JobEnvelope


@dataclass(frozen=True)
class AutonomousJobHandler:
    execute: Callable[[AutonomousRemediationJob], Awaitable[bool]]

    async def __call__(self, envelope: JobEnvelope) -> bool:
        if envelope.job_type != AUTONOMOUS_REMEDIATION:
            return False
        job = AutonomousRemediationJob.from_payload(envelope.payload)
        return await self.execute(job)
