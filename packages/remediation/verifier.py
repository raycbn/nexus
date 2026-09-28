from dataclasses import dataclass
from typing import Any, Protocol

from packages.domain.models.remediation import RemediationAction


@dataclass(frozen=True)
class VerificationResult:
    verified: bool
    message: str
    evidence: dict[str, Any]


class RemediationVerifier(Protocol):
    async def verify(self, action: RemediationAction) -> VerificationResult: ...


class RestartServiceVerifier:
    def __init__(self, service_status_reader) -> None:
        self._service_status_reader = service_status_reader

    async def verify(self, action: RemediationAction) -> VerificationResult:
        service = action.command_preview.rsplit(" ", 1)[-1]
        status = await self._service_status_reader(service)
        verified = status in {"running", "active"}
        return VerificationResult(
            verified=verified,
            message="Service is active" if verified else "Service is not active",
            evidence={"service": service, "status": status},
        )
