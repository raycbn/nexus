from dataclasses import dataclass

from packages.connectors.base.models import ReadResult


@dataclass(frozen=True)
class PreconditionResult:
    passed: bool
    reason: str


def require_resource_enabled(enabled: bool) -> PreconditionResult:
    if not enabled:
        return PreconditionResult(False, "Resource is disabled")
    return PreconditionResult(True, "Resource is enabled")


def require_service_state(result: ReadResult, expected: str = "active") -> PreconditionResult:
    if not result.success:
        return PreconditionResult(False, result.error or "Unable to inspect service state")
    state = str(result.data).strip().splitlines()[0] if result.data else ""
    if state != expected:
        return PreconditionResult(False, f"Service state is {state!r}, expected {expected!r}")
    return PreconditionResult(True, f"Service state is {expected}")
