from uuid import UUID

from packages.domain.models.enums import RiskLevel
from packages.domain.models.remediation import RemediationAction

SUPPORTED_ACTIONS = {"restart_service"}


def build_restart_service_action(
    *,
    organization_id: UUID,
    workspace_id: UUID | None,
    investigation_id: UUID,
    resource_id: UUID,
    service: str,
) -> RemediationAction:
    if not service or service != service.strip():
        raise ValueError("Service name must be non-empty and trimmed")
    if service.startswith("-") or any(char in service for char in ";|&$()<>\"'"):
        raise ValueError("Unsafe service name")
    return RemediationAction(
        organization_id=organization_id,
        workspace_id=workspace_id,
        investigation_id=investigation_id,
        resource_id=resource_id,
        connector_key="linux",
        action_type="restart_service",
        command_preview=f"systemctl restart {service}",
        risk_level=RiskLevel.HIGH,
        requires_approval=True,
        dry_run=True,
    )
