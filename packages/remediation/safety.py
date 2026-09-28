from dataclasses import dataclass

from packages.domain.config import NexusSettings


@dataclass(frozen=True)
class SafetyDecision:
    allowed: bool
    reason: str | None = None


def remediation_kill_switch_enabled(settings: NexusSettings | None = None) -> bool:
    return (settings or NexusSettings()).remediation_kill_switch


def check_kill_switch(settings: NexusSettings | None = None) -> SafetyDecision:
    if remediation_kill_switch_enabled(settings):
        return SafetyDecision(False, "Remediation kill switch is enabled")
    return SafetyDecision(True)
