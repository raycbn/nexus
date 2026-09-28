from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from packages.platform.autonomous_job_handler import AutonomousJobHandler
from packages.platform.job_types import AutonomousRemediationJob
from packages.platform.jobs import JobEnvelope
from packages.remediation.autonomous_service import execute_autonomous_remediation

ContextLoader = Callable[[AutonomousRemediationJob], Awaitable[dict]]


@dataclass(frozen=True)
class AutonomousRemediationWorker:
    load_context: ContextLoader

    async def handle(self, envelope: JobEnvelope) -> bool:
        job = AutonomousRemediationJob.from_payload(envelope.payload)
        context = await self.load_context(job)
        result = await execute_autonomous_remediation(**context)
        return result.loop.decision in {"verified", "simulated"}

    def handler(self) -> AutonomousJobHandler:
        return AutonomousJobHandler(self.handle)
