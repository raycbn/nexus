from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from packages.domain.models.enums import RiskLevel
from packages.domain.models.policy import Policy

_RISK_ORDER = {
    RiskLevel.LOW: 0,
    RiskLevel.MEDIUM: 1,
    RiskLevel.HIGH: 2,
    RiskLevel.CRITICAL: 3,
}


@dataclass(frozen=True)
class GovernanceConfig:
    enabled: bool = False
    max_risk_level: RiskLevel = RiskLevel.MEDIUM
    allow_autonomous_high_risk: bool = False
    allowed_resource_ids: tuple[UUID, ...] = ()
    denied_action_types: tuple[str, ...] = ()
    approval_chain_user_ids: tuple[UUID, ...] = ()
    maintenance_windows: tuple[dict, ...] = ()
    max_affected_resources: int = 1
    rollback_required: bool = False

    def to_policy(self, organization_id: UUID) -> Policy:
        return Policy(
            organization_id=organization_id,
            name="runtime-autonomous-governance",
            max_risk_level=self.max_risk_level,
            allow_autonomous_high_risk=self.allow_autonomous_high_risk,
            allowed_resource_ids=list(self.allowed_resource_ids),
            denied_tool_ids=list(self.denied_action_types),
        )

    def check(
        self,
        *,
        resource_id: UUID,
        action_type: str,
        risk_level: RiskLevel,
        affected_resources: int = 1,
        now: datetime | None = None,
    ) -> list[str]:
        blockers: list[str] = []
        if not self.enabled:
            blockers.append("governance_disabled")
        if _RISK_ORDER[risk_level] > _RISK_ORDER[self.max_risk_level]:
            blockers.append("risk_exceeds_governance_limit")
        if self.allowed_resource_ids and resource_id not in self.allowed_resource_ids:
            blockers.append("resource_not_allowed")
        if action_type in self.denied_action_types:
            blockers.append("action_denied")
        if affected_resources > self.max_affected_resources:
            blockers.append("blast_radius_exceeded")
        if self.maintenance_windows and not self.in_maintenance_window(now):
            blockers.append("outside_maintenance_window")
        if self.rollback_required and action_type != "restart_service":
            blockers.append("rollback_strategy_unavailable")
        return blockers

    def in_maintenance_window(self, now: datetime | None = None) -> bool:
        if not self.maintenance_windows:
            return True
        current = now or datetime.now(UTC)
        if current.tzinfo is None:
            current = current.replace(tzinfo=UTC)
        for window in self.maintenance_windows:
            zone = ZoneInfo(window.get("timezone", "UTC"))
            local = current.astimezone(zone)
            weekday = local.weekday()
            minutes = local.hour * 60 + local.minute
            days = window.get("days", [])
            if days and weekday not in days:
                continue
            start = _minutes(window.get("start", "00:00"))
            end = _minutes(window.get("end", "23:59"))
            if start <= end and start <= minutes <= end:
                return True
            if start > end and (minutes >= start or minutes <= end):
                return True
        return False


def _minutes(value: str) -> int:
    hour, minute = value.split(":", 1)
    return int(hour) * 60 + int(minute)


def from_model(model) -> GovernanceConfig:
    return GovernanceConfig(
        enabled=model.enabled,
        max_risk_level=RiskLevel(model.max_risk_level),
        allow_autonomous_high_risk=model.allow_autonomous_high_risk,
        allowed_resource_ids=tuple(UUID(value) for value in model.allowed_resource_ids),
        denied_action_types=tuple(model.denied_action_types),
        approval_chain_user_ids=tuple(UUID(value) for value in model.approval_chain_user_ids),
        maintenance_windows=tuple(model.maintenance_windows),
        max_affected_resources=model.max_affected_resources,
        rollback_required=model.rollback_required,
    )
