from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from packages.domain.models.remediation import RemediationAction
from packages.remediation.verifier import VerificationResult


@dataclass(frozen=True)
class LabRestartServiceVerifier:
    status_reader: Callable[[str], Awaitable[str]]

    async def verify(self, action: RemediationAction) -> VerificationResult:
        service = action.command_preview.rsplit(" ", 1)[-1]
        status = await self.status_reader(service)
        verified = status in {"running", "active"}
        return VerificationResult(
            verified=verified,
            message="Service is active" if verified else "Service is not active",
            evidence={"service": service, "status": status},
        )
