from packages.domain.models.remediation import RemediationStatus

_ALLOWED: dict[RemediationStatus, set[RemediationStatus]] = {
    RemediationStatus.PROPOSED: {
        RemediationStatus.APPROVED,
        RemediationStatus.REJECTED,
        RemediationStatus.EXECUTING,
    },
    RemediationStatus.APPROVED: {RemediationStatus.EXECUTING, RemediationStatus.REJECTED},
    RemediationStatus.EXECUTING: {RemediationStatus.EXECUTED, RemediationStatus.FAILED},
    RemediationStatus.EXECUTED: {RemediationStatus.VERIFIED, RemediationStatus.FAILED},
    RemediationStatus.VERIFIED: set(),
    RemediationStatus.REJECTED: set(),
    RemediationStatus.FAILED: set(),
}


def validate_transition(current: RemediationStatus, target: RemediationStatus) -> None:
    if target not in _ALLOWED[current]:
        raise ValueError(f"Invalid remediation transition: {current} -> {target}")
