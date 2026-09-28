from enum import StrEnum
from uuid import UUID

from packages.domain.models.base import NexusBaseModel
from packages.domain.models.enums import RiskLevel


class RemediationStatus(StrEnum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    EXECUTING = "executing"
    EXECUTED = "executed"
    VERIFIED = "verified"
    REJECTED = "rejected"
    FAILED = "failed"


class RemediationAction(NexusBaseModel):
    organization_id: UUID
    workspace_id: UUID | None = None
    investigation_id: UUID
    resource_id: UUID
    connector_key: str
    action_type: str
    command_preview: str
    risk_level: RiskLevel
    status: RemediationStatus = RemediationStatus.PROPOSED
    requires_approval: bool = True
    dry_run: bool = True
